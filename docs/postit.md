# TFM post-it

Ideas sueltas / cosas pendientes para no perderlas.

---

## Ahora

- [ ] Generar pool PHOENIX inicial:
  - F5V
  - G2V
  - K5V
  - M0V
  - M2V

- [ ] Usar por ahora:
  - `[Fe/H] = 0.0`
  - estrellas enanas/main sequence
  - rango ESPRESSO: `0.38–0.788 µm`
  - `10000` puntos como grid ligera
  - sin normalización por defecto

- [ ] Documentar breve justificación del pool estelar.

---

## Siguiente bloque grande

- [ ] Automatizar generación de `mtrans` con Molecfit.
- [ ] Variar primero atmósfera, no estrella:
  - PWV
  - airmass
  - moléculas principales

- [ ] Crear primer dataset:

```text
5 estrellas × 20 atmósferas = 100 espectros sintéticos
```

---

## Ideas interesantes

- [ ] Consultar TOIs/TESS para ver rangos reales de hosts:
  - Teff
  - logg
  - [Fe/H]
  - radio
  - masa

- [ ] Comparar nuestro pool PHOENIX con hosts reales de tránsitos.

- [ ] Añadir metalicidad más adelante:
  - `[Fe/H] = -0.3, 0.0, +0.3`

- [ ] Añadir modelo instrumental ESPRESSO real:
  - HR
  - UHR
  - MR

- [ ] Añadir ruido sintético/SNR.

---

## Infra / comodidad

- [ ] Sincronizar `~/TFM_DATA` con Syncthing.
- [ ] Mantener `~/TFM` solo con GitHub.
- [ ] En el futuro: Raspberry como nodo permanente.
- [ ] Futuro dashboard web en Raspberry para ver:
  - estado de sync
  - espacio en disco
  - últimos archivos
  - errores

---

## Preguntas para tutores

- [ ] ¿La red debe predecir espectro corregido o parámetros Molecfit?
- [ ] ¿Qué modo ESPRESSO usamos como referencia?
- [ ] ¿Qué regiones espectrales interesan más para telúricas?
- [ ] ¿Cuánta física instrumental necesita el primer dataset?
