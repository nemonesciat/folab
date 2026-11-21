"""Runs inside the user's own Chatterbox Python (never FOLab's: Chatterbox needs torch, gigabytes FOLab.exe doesn't
carry), started by voicegen.Chatterbox. One JSON request a line on stdin, one JSON answer a line on stdout:
    {"text": ..., "ref": "<a clip of the voice to copy>", "exaggeration": 0.45, "cfg": 0.25, "out": "<.wav to write>"}
    -> {"ok": true, "seconds": 3.2} or {"error": "..."}
The first line out is {"ready": true, "device": "cuda"} once the model is loaded. The model's files come where Hugging
Face keeps them (HF_HOME, which FOLab sets beside the Chatterbox folder). Writes 24,000 a second, mono, float."""
import json
import sys
import traceback


def main():
    out = sys.stdout
    sys.stdout = sys.stderr        # anything the libraries print goes to the log, not the answers
    import numpy as np
    import soundfile
    import torch
    from chatterbox.tts import ChatterboxTTS
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = ChatterboxTTS.from_pretrained(device=device)
    out.write(json.dumps({'ready': True, 'device': device}) + '\n')
    out.flush()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            q = json.loads(line)
            wav = model.generate(q['text'], audio_prompt_path=q['ref'], exaggeration=float(q.get('exaggeration', 0.45)),
                                 cfg_weight=float(q.get('cfg', 0.25)))
            a = wav.squeeze().detach().cpu().numpy().astype(np.float64)
            if model.sr != 24000:
                a = np.interp(np.arange(int(len(a) * 24000 / model.sr)) * model.sr / 24000, np.arange(len(a)), a)
            soundfile.write(q['out'], a.astype(np.float32), 24000, subtype='FLOAT')
            ans = {'ok': True, 'seconds': len(a) / 24000.0}
        except Exception as e:      # noqa: BLE001 - told to FOLab
            traceback.print_exc()
            ans = {'error': '%s: %s' % (type(e).__name__, e)}
        out.write(json.dumps(ans) + '\n')
        out.flush()


if __name__ == '__main__':
    main()
