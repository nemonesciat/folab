// FOLab.exe: starts FOLab (its own Python, no console window), opens it in its own window, and keeps an icon in the
// notification area to open it again, see its log, or quit. Closing FOLab's window quits it.
// (After Morrowind Workshop's launcher.cs.)
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Windows.Forms;

static class Launcher
{
    public static string Root { get { return AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\'); } }

    [STAThread]
    static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        bool first;
        using (var mutex = new Mutex(true, Common.MutexName(Root), out first))
        {
            if (!first)
            {
                // already running: ask it to bring its window to the front
                EventWaitHandle show;
                if (EventWaitHandle.TryOpenExisting(Common.ShowEventName(Root), out show)) show.Set();
                else { string url = Common.RunningUrl(Root); if (url != null) Common.OpenUrl(url); }
                return 0;
            }
            string running = Common.RunningUrl(Root);
            if (running != null) { Common.OpenUrl(running); return 0; }   // started some other way (Start FOLab.bat)
            // FOLab keeps your mods and settings next to itself
            try { string probe = Path.Combine(Root, ".write-test"); File.WriteAllText(probe, ""); File.Delete(probe); }
            catch
            {
                MessageBox.Show("FOLab can't save in this folder:\n" + Root + "\n\nMove the FOLab folder somewhere you can " +
                    "save files, such as Documents or the desktop, and start it from there.",
                    Common.Name, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return 1;
            }
            if (!File.Exists(Path.Combine(Root, "python", "pythonw.exe")))
            {
                MessageBox.Show("FOLab's files are missing (the python folder). Please unzip FOLab again.",
                                Common.Name, MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
            using (var tray = new Tray()) Application.Run(tray);
        }
        return 0;
    }
}

class Tray : ApplicationContext
{
    readonly NotifyIcon icon;
    readonly Process proc;
    readonly StreamWriter logw;
    readonly string logPath;
    readonly SynchronizationContext ui;
    readonly EventWaitHandle showEvent;
    volatile bool inBrowser;
    bool quitting;

    public Tray()
    {
        ui = new WindowsFormsSynchronizationContext();
        SynchronizationContext.SetSynchronizationContext(ui);
        string root = Launcher.Root;
        Directory.CreateDirectory(Path.Combine(root, "logs"));
        logPath = Path.Combine(root, "logs", "folab-console.log");
        try { if (File.Exists(logPath)) File.Copy(logPath, Path.Combine(root, "logs", "folab-console.previous.log"), true); } catch { }
        logw = new StreamWriter(new FileStream(logPath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite), new UTF8Encoding(false));
        logw.AutoFlush = true;
        logw.WriteLine("FOLab " + BuildInfo.Version + " started " + DateTime.Now);

        icon = new NotifyIcon();
        icon.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        icon.Text = "FOLab";
        var menu = new ContextMenuStrip();
        var open = menu.Items.Add("Open FOLab", null, (s, e) => OpenFOLab());
        open.Font = new Font(open.Font, FontStyle.Bold);
        menu.Items.Add("Open in my web browser", null, (s, e) =>
        {
            string url = Common.RunningUrl(Launcher.Root);
            if (url != null) Common.OpenUrl(url);
        });
        menu.Items.Add("Show log", null, (s, e) => ShowLog());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Quit", null, (s, e) => Quit());
        icon.ContextMenuStrip = menu;
        icon.DoubleClick += (s, e) => OpenFOLab();
        icon.Visible = true;
        icon.ShowBalloonTip(4000, "FOLab", "Reading the game: FOLab opens in a few seconds.", ToolTipIcon.Info);

        // pythonw: the windowless Python, made for programs like this one
        var psi = new ProcessStartInfo(Path.Combine(root, "python", "pythonw.exe"),
                                       "-X utf8 \"" + Path.Combine(root, "app", "server.py") + "\" --no-browser");
        psi.WorkingDirectory = root;
        psi.UseShellExecute = false;
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        psi.EnvironmentVariables["FOLAB_NO_BROWSER"] = "1";          // (we open its own window instead)
        psi.EnvironmentVariables.Remove("PYTHONHOME");
        psi.EnvironmentVariables.Remove("PYTHONPATH");
        proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        proc.OutputDataReceived += (s, e) => Log(e.Data);
        proc.ErrorDataReceived += (s, e) => Log(e.Data);
        proc.Exited += (s, e) => ui.Post(_ => OnExited(), null);
        try
        {
            proc.Start();
            proc.BeginOutputReadLine();
            proc.BeginErrorReadLine();
        }
        catch (Exception ex)
        {
            MessageBox.Show("FOLab could not start:\n" + ex.Message, Common.Name, MessageBoxButtons.OK, MessageBoxIcon.Error);
            ExitThread();
            return;
        }
        // starting FOLab again brings its window to the front through this
        showEvent = new EventWaitHandle(false, EventResetMode.AutoReset, Common.ShowEventName(Launcher.Root));
        new Thread(() => { while (true) { showEvent.WaitOne(); ui.Post(_ => OpenFOLab(), null); } }) { IsBackground = true }.Start();

        // open the window as soon as FOLab answers, then quit when that window is closed
        new Thread(() =>
        {
            var sw = Stopwatch.StartNew();
            while (!quitting && Common.RunningUrl(Launcher.Root) == null && sw.ElapsedMilliseconds < 180000) Thread.Sleep(400);
            if (quitting) return;
            ui.Post(_ => OpenFOLab(), null);
            bool seen = false;
            int gone = 0;
            while (!quitting)
            {
                Thread.Sleep(seen ? 1500 : 250);         // (quickly at first: its button is its own as soon as it opens)
                if (inBrowser) return;                   // (no Edge: a browser tab we can't watch)
                AppWindow.IdentifyAll(Application.ExecutablePath);
                bool showing = AppWindow.Windows().Count > 0;
                if (showing) { seen = true; gone = 0; }
                else if (seen && ++gone >= 2) { ui.Post(_ => Quit(), null); return; }
            }
        }) { IsBackground = true }.Start();
    }

    void Log(string line)
    {
        if (line == null) return;
        lock (logw) { try { logw.WriteLine(line); } catch { } }
    }

    void OpenFOLab()
    {
        string url = Common.RunningUrl(Launcher.Root);
        if (url == null) { icon.ShowBalloonTip(4000, "FOLab", "Still reading the game, one moment…", ToolTipIcon.Info); return; }
        bool ok = false;
        try { ok = AppWindow.Show(url); } catch { }
        if (!ok)
        {
            inBrowser = true;
            Common.OpenUrl(url);
            icon.ShowBalloonTip(6000, "FOLab", "It's open in your web browser. Right-click this icon to quit.", ToolTipIcon.Info);
        }
    }

    void ShowLog()
    {
        try { Process.Start(new ProcessStartInfo("notepad.exe", "\"" + logPath + "\"")); } catch { }
    }

    void Quit()
    {
        if (quitting) return;
        quitting = true;
        icon.Text = "FOLab: closing…";
        new Thread(() =>
        {
            try { AppWindow.Close(); } catch { }
            Common.AskToQuit(Launcher.Root, 8000);
            try { if (!proc.HasExited && !proc.WaitForExit(4000)) proc.Kill(); } catch { }
            ui.Post(_ => ExitThread(), null);
        }) { IsBackground = true }.Start();
    }

    void OnExited()
    {
        if (!quitting)
        {
            string tail = "";
            try
            {
                var lines = File.ReadAllLines(logPath, Encoding.UTF8);
                tail = string.Join("\n", lines.Skip(Math.Max(0, lines.Length - 12)));
            }
            catch { }
            var r = MessageBox.Show("FOLab stopped unexpectedly.\n\n" + tail + "\n\nOpen the full log?",
                                    Common.Name, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (r == DialogResult.Yes) ShowLog();
        }
        ExitThread();
    }

    protected override void ExitThreadCore()
    {
        icon.Visible = false;
        base.ExitThreadCore();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            icon.Dispose();
            try { logw.Dispose(); } catch { }
        }
        base.Dispose(disposing);
    }
}
