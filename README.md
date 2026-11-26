# Lirio del valle 3D en ASCII

Un lirio del valle (*Convallaria majalis*) en 3D dibujado con caracteres ASCII.
La planta brota de un punto, crece, abre sus campanas, gira y el viento se lleva sus pétalos.
Luego se marchita y el ciclo vuelve a empezar (18 s).

A sus pies, dos ratitas, una blanca y otra gris, comen queso sentadas muy juntitas y giran con la flor.
Mordisquean a ráfagas: suben el queso a la boca, bajan la cabeza y, entre ráfaga y ráfaga, miran alrededor.
El queso se va gastando a mordiscos durante el ciclo.

## Versión web (la que se abre desde GitHub)

`index.html` es una página autónoma: no tiene dependencias ni necesita servidor.

- **En GitHub Pages:** **https://thudev06.github.io/lirios/**
  Para que funcione, el propietario del repositorio tiene que hacer dos cosas una sola vez:
  1. *Settings → General → Danger Zone → Change visibility → Public*. Con cuenta gratuita,
     GitHub Pages solo publica repositorios públicos.
  2. *Settings → Pages → Build and deployment*: en *Source* elige *Deploy from a branch*,
     selecciona la rama `main` y la carpeta `/ (root)`, y pulsa *Save*.
     Al cabo de 1 o 2 minutos la página estará en línea.
- **Sin internet / desde un pendrive:** copia `index.html` y ábrelo con doble clic en el navegador.

Controles: clic o espacio para pausar, `R` para reiniciar, `F` para pantalla completa.

## Prototipo de escritorio (Python)

`lirios/lirio3d.py` es el prototipo original con pygame y numpy: solo tiene el lirio, sin las ratas.
La versión completa es `index.html`.

```bash
pip install pygame numpy
python lirios/lirio3d.py
python lirios/lirio3d.py --record frames 18   # guarda 18 s de fotogramas PNG sin abrir ventana
```

## Cómo funciona

1. **Geometría:** la escena es una nube de unos 60 000 puntos 3D con normal y material.
   - Tallo: un tubo a lo largo de una curva de Bézier.
   - Campanas: un perfil de revolución con 6 lóbulos curvados, con capa exterior e interior.
   - Hojas: superficies lanceoladas con nervaduras paralelas.
   - Ratas: elipsoides (cuerpo, cabeza, mofletes, ojos, orejas), tubos (brazos y cola) y una cuña
     de queso con agujeros. Se animan por grupos con matrices: la cabeza gira en el cuello y los
     brazos giran en los hombros para subir el queso a la boca.
2. **Proyección:** cada fotograma se rota cada punto y se proyecta en perspectiva sobre una rejilla de celdas de texto.
3. **Z-buffer por celda:** en cada celda gana el punto más cercano a la cámara.
4. **Iluminación Lambert:** el brillo de cada celda elige un carácter de la rampa ` .,:;-=+*cox%#&@`.
5. **Bloom:** se reduce la imagen, se oscurece y se suma encima para dar un brillo suave.
