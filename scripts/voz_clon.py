"""Prueba de clonación de voz: la voz del plató (edge-tts) con el timbre de una grabación de referencia.

Usa el conversor de timbre de OpenVoice V2 (licencia MIT): edge-tts pone la entonación en español
y OpenVoice cambia el timbre por el de la grabación. No hace falta transcribir la referencia.

Uso: python3 scripts/voz_clon.py videos/voz/referencia.mp3 salida/voz
Necesita OpenVoice en PYTHONPATH y el conversor en $OPENVOICE_CKPT (config.json + checkpoint.pth)."""
import asyncio, os, subprocess, sys
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
VOZ, RATE, PITCH = "es-ES-AlvaroNeural", "+12%", "-6Hz"
PRUEBA = [
    "Muy buenas, colchoneros. Esto es Diario Colchonero.",
    "El Atlético perdió uno a dos contra el Barcelona en el Metropolitano, con dos goles de Fermín López.",
    "Giuliano adelantó al Atleti en el minuto diez, tras un centro buenísimo de Julián Álvarez.",
    "Ahora llega el parón de selecciones. ¿Se puede pelear todavía la Liga? Os leo en comentarios.",
]
FUENTE = [  # frases de la voz original para medir su timbre
    "Hoy repasamos toda la actualidad del Atlético de Madrid, con los fichajes y las declaraciones de la semana.",
    "Simeone prepara el próximo partido con varias novedades en el once, y la afición llenará el estadio.",
    "En la clasificación, el equipo sigue en la pelea por los puestos de arriba, a pocos puntos del líder.",
    "Oblak volvió a ser decisivo bajo palos, con tres paradas de mucho mérito en la segunda parte.",
]

def ff(*a):
    subprocess.run([FF, "-y", "-loglevel", "error", *a], check=True)

def tts(texto, wav):
    import edge_tts
    mp3 = wav[:-4] + ".mp3"
    asyncio.run(edge_tts.Communicate(texto, VOZ, rate=RATE, pitch=PITCH).save(mp3))
    ff("-i", mp3, "-ac", "1", "-ar", "22050", wav)

def trozos_referencia(ref, carpeta):
    """Limpia la grabación (graves, ruido, volumen), quita silencios y la corta en trozos de unos 8 s."""
    limpio = os.path.join(carpeta, "ref_limpia.wav")
    ff("-i", ref, "-af", "highpass=f=70,afftdn=nf=-25,loudnorm=I=-18:TP=-2,"
       "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.4:stop_threshold=-45dB",
       "-ac", "1", "-ar", "22050", limpio)
    ff("-i", limpio, "-f", "segment", "-segment_time", "8", "-c", "copy", os.path.join(carpeta, "ref_%02d.wav"))
    trozos = sorted(os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.startswith("ref_") and f[4:6].isdigit())
    return [t for t in trozos if os.path.getsize(t) > 22050 * 2 * 2], limpio   # al menos ~2 s

def main(ref, salida):
    import torch
    from openvoice.api import ToneColorConverter
    os.makedirs(salida, exist_ok=True)
    tmp = os.path.join(salida, "tmp"); os.makedirs(tmp, exist_ok=True)
    ck = os.environ["OPENVOICE_CKPT"]
    tcc = ToneColorConverter(os.path.join(ck, "config.json"), device="cpu")
    tcc.watermark_model = None   # sin marca de agua de audio
    tcc.load_ckpt(os.path.join(ck, "checkpoint.pth"))
    trozos, limpio = trozos_referencia(ref, tmp)
    print("Trozos de la grabación:", len(trozos))
    tgt = tcc.extract_se(trozos)
    fuentes = []
    for i, t in enumerate(FUENTE):
        w = os.path.join(tmp, f"fuente_{i}.wav"); tts(t, w); fuentes.append(w)
    src = tcc.extract_se(fuentes)
    torch.save(src.cpu(), os.path.join(salida, "timbre_alvaro.pth"))
    originales, clonadas = [], []
    for i, t in enumerate(PRUEBA):
        w = os.path.join(tmp, f"prueba_{i}.wav"); tts(t, w); originales.append(w)
        for tau in (0.3, 0.5):
            o = os.path.join(tmp, f"clon_{tau}_{i}.wav")
            tcc.convert(audio_src_path=w, src_se=src, tgt_se=tgt, output_path=o, tau=tau)
            clonadas.append((tau, o))

    def unir(lista, destino):
        txt = os.path.join(tmp, "lista.txt")
        with open(txt, "w") as f:
            for x in lista:
                f.write(f"file '{os.path.abspath(x)}'\n")
        ff("-f", "concat", "-safe", "0", "-i", txt, "-ar", "44100", "-b:a", "160k", destino)

    unir(originales, os.path.join(salida, "1_voz_actual.mp3"))
    unir([o for tau, o in clonadas if tau == 0.3], os.path.join(salida, "2_tu_voz_A.mp3"))
    unir([o for tau, o in clonadas if tau == 0.5], os.path.join(salida, "3_tu_voz_B.mp3"))
    print("Listo:", sorted(os.listdir(salida)))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
