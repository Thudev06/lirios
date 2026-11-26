# Lirio del valle 3D en ASCII

Un lirio del valle (*Convallaria majalis*) en 3D dibujado con caracteres ASCII.
La planta brota de un punto, crece, abre sus campanas, gira y el viento se lleva sus pétalos.
Luego se marchita y el ciclo vuelve a empezar (18 s).

## Versión web (la que se abre desde GitHub)

`index.html` es una página autónoma: no tiene dependencias ni necesita servidor.

- **En GitHub Pages:** ve a *Settings → Pages → Build and deployment*, elige
  *Deploy from a branch*, selecciona la rama y la carpeta `/ (root)`, y guarda.
  Al cabo de uno o dos minutos estará en `https://<usuario>.github.io/<repo>/`.
- **Sin internet / desde un pendrive:** copia `index.html` y ábrelo con doble clic en el navegador.

Controles: clic o espacio para pausar, `R` para reiniciar, `F` para pantalla completa.

## Versión de escritorio (Python)

`lirios/lirio3d.py` es la versión original con pygame y numpy.

```bash
pip install pygame numpy
python lirios/lirio3d.py
python lirios/lirio3d.py --record frames 18   # guarda 18 s de fotogramas PNG sin abrir ventana
```

## Cómo funciona

1. **Geometría:** la planta es una nube de unos 51 000 puntos 3D con normal y material.
   - Tallo: un tubo a lo largo de una curva de Bézier.
   - Campanas: un perfil de revolución con 6 lóbulos curvados, con capa exterior e interior.
   - Hojas: superficies lanceoladas con nervaduras paralelas.
2. **Proyección:** cada fotograma se rota cada punto y se proyecta en perspectiva sobre una rejilla de celdas de texto.
3. **Z-buffer por celda:** en cada celda gana el punto más cercano a la cámara.
4. **Iluminación Lambert:** el brillo de cada celda elige un carácter de la rampa ` .,:;-=+*cox%#&@`.
5. **Bloom:** se reduce la imagen, se oscurece y se suma encima para dar un brillo suave.
