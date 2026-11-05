// FOLab.exe's helpers: is FOLab running from this folder, ask it to quit, open a link.
// (After Morrowind Workshop's launcher, packaging/common.cs there.)
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using System.Threading;

static class Common
{
    public const string Name = "FOLab";

    // Names for "is it running?" and "show your window", one set per folder (copies in different folders keep apart)
    public static string Tag(string root)
    {
        using (var sha = System.Security.Cryptography.SHA1.Create())
        {
            var h = sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(Path.GetFullPath(root).TrimEnd('\\').ToLowerInvariant()));
            return BitConverter.ToString(h, 0, 6).Replace("-", "");
        }
    }
    public static string MutexName(string root) { return "FOLab.Launcher." + Tag(root); }
    public static string ShowEventName(string root) { return "FOLab.ShowRequest." + Tag(root); }

    public static string RunningFile(string root) { return Path.Combine(root, "folab_running.json"); }

    // The address of a FOLab running from this folder (its process alive and its port answering), or null.
    public static string RunningUrl(string root)
    {
        try
        {
            string text = File.ReadAllText(RunningFile(root));
            Match m = Regex.Match(text, "\"url\"\\s*:\\s*\"([^\"]+)\"");
            Match pid = Regex.Match(text, "\"pid\"\\s*:\\s*(\\d+)");
            Match port = Regex.Match(text, "\"port\"\\s*:\\s*(\\d+)");
            if (!m.Success || !pid.Success || !port.Success) return null;
            using (var p = Process.GetProcessById(int.Parse(pid.Groups[1].Value)))
                if (p.HasExited) return null;
            using (var c = new System.Net.Sockets.TcpClient())
            {
                if (!c.ConnectAsync("127.0.0.1", int.Parse(port.Groups[1].Value)).Wait(2000)) return null;
                return m.Groups[1].Value;
            }
        }
        catch { return null; }
    }

    // Ask a running FOLab to stop (everything is saved as it's made). True when it has stopped.
    public static bool AskToQuit(string root, int waitMs)
    {
        string url = RunningUrl(root);
        if (url == null) return true;
        try
        {
            var req = (HttpWebRequest)WebRequest.Create(url + "api/quit");
            req.Method = "POST";
            req.Timeout = 3000;
            req.Proxy = null;
            req.ContentLength = 0;
            req.Headers.Add("X-FOLab-Quit", "1");
            using (req.GetResponse()) { }
        }
        catch { }
        var sw = Stopwatch.StartNew();
        while (sw.ElapsedMilliseconds < waitMs)
        {
            Thread.Sleep(250);
            if (RunningUrl(root) == null) return true;
        }
        return false;
    }

    public static void OpenUrl(string url)
    {
        try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); } catch { }
    }
}
