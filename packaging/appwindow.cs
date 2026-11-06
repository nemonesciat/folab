// FOLab's own window: Microsoft Edge (part of Windows 10 and 11) in app mode, with no tabs or address bar and a
// taskbar button of its own. It uses your normal Edge profile on purpose: a separate Edge settings folder gets signed
// in to your Microsoft account by Edge itself, which FOLab must never cause. The window is found by its title (an app
// window's title is the page's own: "FOLab"), and only that window is ever closed, never Edge itself. Without Edge,
// FOLab opens in your default browser instead. (After Morrowind Workshop's appwindow.cs.)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

static class AppWindow
{
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);

    const string Title = "FOLab";

    public static string FindEdge()
    {
        foreach (var hive in new[] { Registry.CurrentUser, Registry.LocalMachine })
        {
            try
            {
                using (var k = hive.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"))
                {
                    var p = k == null ? null : k.GetValue(null) as string;
                    if (!string.IsNullOrEmpty(p) && File.Exists(p)) return p;
                }
            }
            catch { }
        }
        foreach (var pf in new[] { Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                                   Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) })
        {
            string p = Path.Combine(pf, "Microsoft", "Edge", "Application", "msedge.exe");
            if (File.Exists(p)) return p;
        }
        return null;
    }

    // Edge windows showing FOLab (normal Edge windows are titled "... - Microsoft Edge")
    public static List<IntPtr> Windows()
    {
        var edge = new HashSet<uint>();
        try { foreach (var p in Process.GetProcessesByName("msedge")) edge.Add((uint)p.Id); } catch { }
        var found = new List<IntPtr>();
        if (edge.Count == 0) return found;
        EnumWindows((h, l) =>
        {
            uint pid;
            GetWindowThreadProcessId(h, out pid);
            if (edge.Contains(pid) && IsWindowVisible(h))
            {
                var sb = new StringBuilder(256);
                GetWindowText(h, sb, sb.Capacity);
                if (sb.ToString() == Title) found.Add(h);
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    // Show FOLab: bring its window to the front, or open it. False when Edge isn't there.
    public static bool Show(string url)
    {
        foreach (var h in Windows())
        {
            if (IsIconic(h)) ShowWindow(h, 9);              // (restore if minimised)
            SetForegroundWindow(h);
            return true;
        }
        string edge = FindEdge();
        if (edge == null) return false;
        Process.Start(new ProcessStartInfo(edge, "--app=\"" + url + "\" --window-size=1600,960") { UseShellExecute = false });
        return true;
    }

    // ---------- a taskbar button of its own ----------
    // Windows groups taskbar buttons by an ID on the window. Left alone, FOLab's has what Edge gives it, which other Edge
    // app windows can share (Morrowind Workshop's is one), so they stack on one button. Here it gets FOLab's own, with its
    // icon and FOLab.exe to start it again when pinned. Only FOLab's own window is ever touched.
    const string TaskbarId = "FOLab.Editor";
    static readonly Guid AppUserModelProps = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
    const uint PropId = 5, PropRelaunchCommand = 2, PropRelaunchIcon = 3, PropRelaunchName = 4;
    static readonly HashSet<IntPtr> identified = new HashSet<IntPtr>();

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PropKey { public Guid Set; public uint Id; public PropKey(Guid s, uint i) { Set = s; Id = i; } }

    [StructLayout(LayoutKind.Sequential)]
    struct PropValue { public ushort Type, R1, R2, R3; public IntPtr Value, Rest; }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore
    {
        void GetCount(out uint n);
        void GetAt(uint i, out PropKey key);
        void GetValue(ref PropKey key, out PropValue value);
        void SetValue(ref PropKey key, ref PropValue value);
        void Commit();
    }

    [DllImport("shell32.dll", PreserveSig = false)]
    static extern void SHGetPropertyStoreForWindow(IntPtr h, ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out IPropertyStore store);
    [DllImport("ole32.dll")] static extern int PropVariantClear(ref PropValue v);

    static IPropertyStore StoreOf(IntPtr h)
    {
        Guid iid = typeof(IPropertyStore).GUID;
        IPropertyStore store;
        SHGetPropertyStoreForWindow(h, ref iid, out store);
        return store;
    }

    static void SetText(IPropertyStore store, uint id, string text)
    {
        var key = new PropKey(AppUserModelProps, id);
        var v = new PropValue { Type = 31, Value = Marshal.StringToCoTaskMemUni(text) };     // VT_LPWSTR
        try { store.SetValue(ref key, ref v); }
        finally { Marshal.FreeCoTaskMem(v.Value); }
    }

    public static void Identify(IntPtr h, string exe)
    {
        IPropertyStore store = StoreOf(h);
        try
        {
            // (the three go together, the ID last: pinning reads them when the ID arrives)
            SetText(store, PropRelaunchCommand, "\"" + exe + "\"");
            SetText(store, PropRelaunchName, Title);
            SetText(store, PropRelaunchIcon, exe + ",0");
            SetText(store, PropId, TaskbarId);
            store.Commit();
        }
        finally { Marshal.ReleaseComObject(store); }
    }

    public static string IdentityOf(IntPtr h)
    {
        IPropertyStore store = StoreOf(h);
        try
        {
            var key = new PropKey(AppUserModelProps, PropId);
            PropValue v;
            store.GetValue(ref key, out v);
            try { return v.Type == 31 ? Marshal.PtrToStringUni(v.Value) : null; }
            finally { PropVariantClear(ref v); }
        }
        finally { Marshal.ReleaseComObject(store); }
    }

    // Any FOLab window that hasn't its own button yet gets one. (Asked often: a new window has none until its page loads
    // and gives it its title.) If Windows refuses, the window still works, on a shared button.
    public static void IdentifyAll(string exe)
    {
        foreach (var h in Windows())
        {
            if (identified.Contains(h)) continue;
            try { Identify(h, exe); identified.Add(h); } catch { }
        }
    }

    // Close FOLab's window (quitting from the tray), the way its ✕ does.
    public static void Close()
    {
        foreach (var h in Windows()) PostMessage(h, 0x0112, (IntPtr)0xF060, IntPtr.Zero);   // WM_SYSCOMMAND, SC_CLOSE
    }
}
