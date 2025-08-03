# Record Plotter

- Numpy/polars-oriented lev/rec loading
- Get recs/levs from EOL
- Produce plotly static view of recs
- Procuce markdown table summary of recent recs

Example usage:

```bash
elma-recplot get-lev 4 --outfile QWQUU002.lev
elma-recplot get-rec b7qib5hln4 02j.rec --outfile 02j.rec
elma-recplot plot-rec QWQUU002.lev  02j.rec --outfile 02j.html
```

Example output  [02j.html](https://simon-b.github.io/elma-recplot-page/recs/02j.html)