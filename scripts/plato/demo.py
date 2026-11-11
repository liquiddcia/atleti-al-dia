"""Demo del plató: el presentador abre en plano general y luego cuenta dos imágenes en la pantalla.
Uso: python3 scripts/plato/demo.py salida/plato_demo.mp4"""
import asyncio, os, subprocess, sys, wave
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.join(AQUI, "..", "..")
sys.path.insert(0, AQUI)
import plato_render as pr
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
from nombres import nombres, pronunciar
FF = os.environ.get("FF", "ffmpeg"); pr.FFMPEG = FF
SR = 44100
P = lambda *r: os.path.join(RAIZ, "videos", "plato", *r)

GUION = [
    ("centro", None, "Buenas noches, colchoneros. Bienvenidos a Diario Colchonero. Hoy, noche grande de Champions: el Atlético recibe al Bayern de Múnich en el Metropolitano."),
    ("pantalla", P("demo", "01_portada.png"), "El partido se juega este martes, a las nueve de la noche. Y el Bayern llega solo un punto por delante en la fase de liga."),
    ("pantalla", P("demo", "02_momento.png"), "El Atlético llega lanzado: nueve partidos sin perder y siete victorias seguidas en Liga. Pero en Europa necesita sumar."),
]

PAUSA = "__PAUSA__"
AUDIO = "__AUDIO__:"   # prefijo de una frase grabada por el autor (ruta a su audio)
HUECO = 0.3        # silencio entre frases (s); el json puede cambiarlo con "hueco"
VELOCIDAD = "+12%"  # velocidad de la voz; el json puede cambiarla con "velocidad"   # tramo sin voz (por ejemplo, la imagen del canal al final)

def voz(texto, wav):
    if texto == PAUSA:
        return np.zeros(int(2.2 * SR), dtype=np.float32)
    if texto.startswith(AUDIO):   # frase grabada por el autor: se usa su audio tal cual (limpio y nivelado)
        ruta = texto[len(AUDIO):]
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", ruta, "-af",
                        "highpass=f=70,afftdn=nf=-25,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5",
                        "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", wav], check=True)
        with wave.open(wav) as w:
            return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    texto = pronunciar(nombres(texto))
    import edge_tts
    mp3 = wav.replace(".wav", ".mp3")
    asyncio.run(edge_tts.Communicate(texto, "es-ES-AlvaroNeural", rate=VELOCIDAD, pitch="-6Hz").save(mp3))
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-af",
                    "aresample=44100,silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.18:stop_threshold=-45dB:stop_silence=0.15,bass=g=3:f=120,acompressor=threshold=0.1:ratio=2.5:attack=20:release=250",
                    "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", wav], check=True)
    with wave.open(wav) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768

def guardar(x, ruta):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())

def ambiente(n):
    t = np.arange(n) / SR; m = np.zeros(n)
    acordes = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    paso = 6.0
    for c in range(int(n / SR / paso) + 2):
        a0 = int(c * paso * SR); a1 = min(int((c + 1.6) * paso * SR), n)
        if a0 >= n: break
        tt = np.arange(a1 - a0) / SR; env = np.sin(np.pi * np.clip(tt / ((a1 - a0) / SR), 0, 1)) ** 2
        ac = acordes[c % 4]
        m[a0:a1] += env * (0.05 * sum(np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt) for f in ac) + 0.06 * np.sin(np.pi * ac[0] * tt))
    m *= np.minimum(t / 1.5, 1) * np.minimum((t[-1] - t) / 1.5, 1)
    return 0.22 * m / (np.max(np.abs(m)) or 1)

def main(salida, render=None):
    tmp = os.path.join(os.path.dirname(os.path.abspath(salida)), "plato_tmp"); os.makedirs(tmp, exist_ok=True)
    partes, tramos, t = [], [], 0.6
    pista = [np.zeros(int(0.6 * SR))]
    for i, (plano, slide, texto) in enumerate(GUION):
        x = voz(texto, os.path.join(tmp, f"v{i}.wav"))
        ini = t; t += len(x) / SR + HUECO
        if tramos and tramos[-1][2] == plano and tramos[-1][3] == slide:
            tramos[-1] = (tramos[-1][0], t, plano, slide)   # misma imagen: se alarga el tramo
        else:
            tramos.append((0 if i == 0 else ini, t, plano, slide))
        pista += [x, np.zeros(int(HUECO * SR))]
    pista.append(np.zeros(int(1.0 * SR)))
    v = np.concatenate(pista); tramos[-1] = (tramos[-1][0], len(v) / SR, tramos[-1][2], tramos[-1][3])
    guardar(v, os.path.join(tmp, "voz.wav")); guardar(ambiente(len(v)), os.path.join(tmp, "musica.wav"))
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(tmp, "voz.wav"), "-i", os.path.join(tmp, "musica.wav"), "-filter_complex",
                    "[0]asplit[v][k];[1][k]sidechaincompress=threshold=0.04:ratio=3:attack=30:release=400[m];[v][m]amix=inputs=2:normalize=0,alimiter=limit=0.95",
                    os.path.join(tmp, "final.wav")], check=True)
    for tr in tramos: print("tramo", tr[2], round(tr[0], 2), "→", round(tr[1], 2), flush=True)
    (render or (lambda tr, voz_, sal, fin: pr.render(P("fondos", "escudo_centro.png"), P("fondos", "escudo_pantalla.png"),
                                                    P("presentador.png"), tr, voz_, sal, fin)))(
        tramos, os.path.join(tmp, "voz.wav"), salida, os.path.join(tmp, "final.wav"))
    print("Vídeo listo:", salida)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "salida/plato_demo.mp4")
