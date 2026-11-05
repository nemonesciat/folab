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

    // Close FOLab's window (quitting from the tray), the way its ✕ does.
    public static void Close()
    {
        foreach (var h in Windows()) PostMessage(h, 0x0112, (IntPtr)0xF060, IntPtr.Zero);   // WM_SYSCOMMAND, SC_CLOSE
    }
}
