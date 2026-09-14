# YGO Scan — valore delle carte Yu-Gi-Oh! dalla camera del telefono

App web (PWA) ispirata allo scanner Pokémon "Acorn TCG" (analisi del video: `ANALISI-VIDEO.md`):
inquadri una carta nel riquadro, in meno di mezzo secondo compare il prezzo sopra la carta, la
miniatura entra nella pila in basso a sinistra, il totale si aggiorna. "Organizza" mostra la griglia
delle carte scansionate con la stampa scelta e i prezzi; da lì si cambia stampa, si rimuove, si copia il CSV.

Nessun server, nessuna app da installare dagli store: si apre nel browser del telefono e si aggiunge
alla schermata Home. Tutto il riconoscimento gira sul telefono.

## Come funziona

1. `build_db.py` scarica UNA volta l'elenco carte da [YGOPRODeck](https://ygoprodeck.com/api-guide/)
   (14.559 carte: tutto il pool OCG/TCG dal primo set del 2002 ai set in uscita, 1.035 set, illustrazioni
   alternative comprese; nomi inglesi e italiani; prezzi Cardmarket € e TCGplayer $; stampe con codice set
   e rarità) e le immagini piccole delle carte in `data/small/` (policy YGOPRODeck: scaricare e ri-ospitare,
   mai hotlink). Per ogni immagine calcola tre hash percettivi (pHash dell'illustrazione, pHash e dHash
   dell'intera carta) e scrive `docs/db.json` (~3,3 MB). Fuori dal database: solo le carte Rush Duel
   (gioco separato, non presente nell'API).
   **Aggiornamento automatico:** `.github/workflows/update-db.yml` rilancia la build ogni lunedì su GitHub
   (riusa gli hash esistenti, scarica solo le immagini nuove) e pubblica carte nuove + prezzi freschi.
2. `docs/index.html` legge il db, apre la camera e ~10 volte al secondo ritaglia il riquadro guida,
   prova una griglia di posizioni/scale (75 + 27 di raffinamento), calcola l'hash dell'illustrazione e
   lo confronta con tutte le 14.723 immagini del db (distanza di Hamming). Le immagini entro 4 bit dal
   minimo formano una shortlist; su questa si calcola il punteggio combinato S = illustrazione + carta
   intera (pHash + dHash). Il migliore viene accettato solo se: illustrazione ≤ 14 bit, S ≤ 40 bit,
   margine sul secondo ≥ 6 bit, e la stessa carta vince su 2 frame consecutivi. Poi resta "bloccato"
   finché la carta non esce dal riquadro (3 frame senza match), così una carta non viene contata due volte.
   Ad ogni carta contata suona una "monetina" (sintetizzata con Web Audio, pulsante "Suono" per spegnerla).
3. Il prezzo mostrato è il **minimo Cardmarket della carta** (livello carta, non stampa: l'API Cardmarket
   non è aperta). Per ogni stampa è disponibile il prezzo **TCGplayer in $**: la stampa di default è
   la più economica (di solito la comune, scelta prudente), si cambia con un tap.

## Avvio

```bash
python build_db.py            # prima volta: ~1 ora di download (riprende da dove era rimasto), poi hash
python test_match.py          # check: riconoscimento simulato ≥ 90%, zero scambi, zero vuoti accettati
python serve.py               # https://<ip-del-pc>:8443 sul telefono (stessa Wi-Fi, accettare il certificato)
```

## Farla provare agli amici (link pubblico)

La cartella `docs/` è un sito statico: GitHub Pages la pubblica gratis con HTTPS (necessario per la camera).

1. Una volta sola: `gh auth login` (si apre il browser, accedi al tuo GitHub).
2. Doppio clic su `deploy.cmd`: crea il repository pubblico `ygoscan`, carica i file e attiva Pages.
3. Il link è `https://<tuo-utente>.github.io/ygoscan/` (attivo entro 1-2 minuti). Gli amici lo aprono sul
   telefono, danno il permesso alla camera e, se vogliono, "Aggiungi a schermata Home".

Ogni volta che cambi qualcosa (o rilanci `build_db.py` per i prezzi aggiornati) basta rilanciare `deploy.cmd`.
Per toglierla da internet: `gh repo delete ygoscan --yes`.

Prova rapida senza camera: il pulsante 🖼 scansiona una foto (la carta deve riempire il riquadro centrale).
Con `?debug` nell'URL la barra di stato mostra le distanze del miglior candidato.

## Limiti onesti (v1)

- Riconosce la **carta**, non la **stampa**: illustrazione uguale = stesso match. Il codice set stampato
  sotto l'illustrazione (es. `LOB-EN005`) permetterebbe di scegliere la stampa in automatico con OCR:
  è la prima cosa da aggiungere (fase 2), oggi si sceglie con un tap.
- Carte con illustrazione gemella possono non essere accettate per il criterio del margine: meglio un
  rifiuto che un prezzo sbagliato; in quel caso "Aggiungi per nome" (italiano o inglese) copre il 100%.
- Test sul database completo (`test_match.py`, camera simulata): 92% riconosciute al primo frame, 89% con
  la conferma su due frame, 0 carte scambiate, 0 falsi positivi su 180 negativi (carte sconosciute e
  inquadrature vuote).
- Foil con riflessi forti, carte in bustina scura, luce scarsa: il match può richiedere qualche
  istante o fallire; un supporto fisso come nel video (telefono fermo, carta sotto) è l'ideale.
- Prezzo Cardmarket = minimo tra tutte le stampe; TCGplayer per stampa in $. Nessuna conversione.
- I dati si aggiornano rilanciando `build_db.py` (le immagini già scaricate non vengono riscaricate).

## Verifica

- `python build_db.py --selftest` — gli hash sono stabili e distinguono immagini diverse.
- `python test_match.py` — simulazione camera (posa, prospettiva, riflessi, luce, sfocatura, rumore, jpeg).
- Parità Python ↔ JS: `data/test/expected.json` contiene i risultati Python sulle foto di prova;
  nel browser `ygo.scanStill('/data/test/photo_0.jpg')` deve dare la stessa carta e distanze simili.
