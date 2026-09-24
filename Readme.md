# Atleti al Día — web que se actualiza sola

Esta carpeta es un proyecto completo para desplegar en **Vercel**. Cada pocas
horas, un cron:

1. Lee varios feeds RSS de noticias del Atlético de Madrid (por defecto,
   Google News, que ya agrega Marca, AS, Mundo Deportivo, ESPN, etc.).
2. Envía cada titular + resumen a la API de Claude para que lo **reescriba
   con voz propia** (nunca se copia el texto original).
3. Guarda el resultado en una base de datos clave-valor (Vercel KV).
4. La página web (`public/index.html`) simplemente muestra lo último guardado.

## 1. Requisitos

- Cuenta gratuita en [vercel.com](https://vercel.com)
- Una API key de Anthropic (console.anthropic.com → API Keys)
- Node.js instalado en tu ordenador (para usar el comando `vercel`)

## 2. Desplegar

```bash
npm install -g vercel
cd atletico-auto
vercel
