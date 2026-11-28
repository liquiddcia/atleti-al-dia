"""Pone una imagen de portada (la miniatura) al principio de un vídeo ya hecho."""
import os, subprocess
import plato_render as pr

def poner(ruta, video, destino, w, h, seg=1.6, fps=30):
    subprocess.run([pr.FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(fps), "-t", str(seg), "-i", ruta,
                    "-i", video, "-filter_complex",
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=yuv420p,"
                    f"zoompan=z='1+0.0008*on':d=1:s={w}x{h}:fps={fps},fade=t=out:st={seg - 0.25}:d=0.25[a];"
                    f"[1:v]setsar=1,format=yuv420p[b];[a][b]concat=n=2:v=1:a=0[v];"
                    f"[1:a]adelay={int(seg * 1000)}|{int(seg * 1000)}[au]",
                    "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", destino], check=True)
    os.remove(video)
    print("Portada añadida al principio:", destino)
