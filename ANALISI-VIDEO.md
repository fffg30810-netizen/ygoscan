# Analisi frame-per-frame — reel Acorn TCG (scanner Pokémon)

Sorgente: `WhatsApp Video 2026-09-14 at 10.39.23.mp4` — 38,2 s, 928 frame a 24,27 fps, 576×1296 (registrazione schermo Instagram, reel di @acorntcg, "pov: collecting pokemon cards but it's 2081"). Estratti 101 frame (uno ogni 0,5 s + 27 cambi di scena rilevati per differenza tra frame) e ispezionati su contact sheet più zoom sui frame chiave.

App inquadrata: **Acorn TCG – Card Scanner** (iOS, id 6740246597). Dichiarato dallo store: scansione in ~1 s, scansione multi-carta, prezzi TCGplayer / Cardmarket / eBay, oltre 40.000 carte, scelta tra camera wide e ultra-wide per l'uso con un supporto fisso ("Card Slinger").

## Timeline

| Tempo | Frame | Cosa succede | Elemento UI / lezione |
|---|---|---|---|
| 0,0–0,5 s | 0–12 | Chat Instagram, apertura del reel | — |
| 0,5–6,0 s | 12–146 | Apertura bustina Pokémon "Black Bolt", estrazione carte + codice TCG Live | Contesto: pacchetto appena aperto, l'utente vuole sapere subito quanto vale |
| 6,0–8,0 s | 146–194 | Il telefono è montato su un **supporto rigido verde** (stampa 3D) inclinato sopra una base bianca; la camera guarda il piano. L'utente appoggia la prima carta (Fraxure) sotto il telefono | **Postazione fissa** = distanza e inquadratura costanti → riconoscimento facile e velocissimo. Questo è il segreto della velocità, più dell'algoritmo |
| 8,0–9,9 s | 194–239 | Zoom sullo schermo: vista camera a tutto schermo, barra in alto con pillola controlli (torcia / camera / ecc.), etichetta di stato in alto a sinistra ("Scanning" / "Paused") | Stato esplicito e minimale, nessun pulsante "scatta": la scansione è **continua** |
| 10,0 s | 243 | Compare l'overlay prezzo **"$0.00"** in basso a destra e il bottone arancione **"Organize (0)"** | Il layout è già pronto prima del primo match: totale e contatore partono da zero |
| 10,1–10,5 s | 245–255 | Match: sulla carta appare **"$0.12"** in grande, bianco con ombra, sovrapposto all'artwork (stile AR). In basso a sinistra compare la **miniatura della carta** (foto reale della scansione) con badge rosso "1", sotto il nome e il set. Totale → **$0.12**, bottone → **Organize (1)** | Feedback in **< 0,5 s** dal posizionamento. Tre informazioni sole: prezzo sulla carta, pila delle miniature, totale corrente |
| 10,5–35,5 s | 255–861 | Sequenza rapida di 10 carte: Fraxure 0,12 → Venipede 0,09 → Servine 0,12 → Rufflet 0,12 → Escavalier 0,12 → Eelektross 0,15 → Energy Coin 0,11 → N's Plan 0,98 → Venipede 0,19 → Victini 0,20. Totale finale **$2.20**, "Organize (10)". Ritmo medio **~2,5 s per carta**, incluso il gesto manuale | La carta si toglie e si mette la successiva: nessun tap. Sui frame 595–655 l'utente tocca la carta N's Plan sullo schermo → il prezzo cambia da 0,23 → 0,35 → 0,98: sta **scegliendo la variante/stampa** (stessa illustrazione, rarità diverse). Lezione: il riconoscimento dell'illustrazione non basta, serve la scelta della stampa |
| 35,5–37,3 s | 861–904 | Tap su "Organize": schermata **"10 cards scanned"**, totale in alto ($2.20), riga del set ("Black Bolt · 10 scans"), **griglia 2 colonne**: foto della carta, pillola di rarità/condizione in alto a sinistra ("Normal", "Holo", "Reverse Holo", "Poké Ball Holo"), badge verde in basso a destra, sotto **nome + prezzo in rosso**. In basso: barra di ricerca "Filter scans", pulsante griglia, pulsante cronologia; in alto a destra "edit" e "+" | La lista è la seconda schermata, non la prima: prima si scansiona, poi si organizza |
| 37,3–38,2 s | 904–928 | Reveal dell'icona: **"Acorn"**, ghianda gialla con occhio da Pokéball su sfondo rosa | Branding |

## Struttura dell'interfaccia (da replicare)

Schermata 1 — Scanner (tutto schermo, camera live):

1. In alto: stato ("Scansione…" / "In pausa"), pillola con torcia e cambio camera.
2. Al centro: la carta inquadrata; al match, **prezzo grande sovrapposto alla carta** (bianco, ombra, ~48 px) e un bordo/vignetta colorata che pulsa come conferma.
3. In basso a sinistra: **pila delle miniature** delle carte scansionate (foto vera), con badge del conteggio; sotto nome e set della carta corrente.
4. In basso a destra: **Totale** (etichetta piccola rossa, importo grande).
5. Bottone arancione **"Organizza (N)"** — apre la schermata 2.

Schermata 2 — Lista scansioni:

1. Titolo "N carte scansionate", totale, riga del set prevalente.
2. Griglia a 2 colonne: foto, pillola variante/rarità, nome, prezzo in rosso; tap → scelta della stampa o rimozione.
3. Barra filtro + icona griglia/lista + cronologia.

## Cosa cambia per Yu-Gi-Oh (vantaggi e trappole)

- **Vantaggio:** ogni stampa Yu-Gi-Oh ha un **codice set stampato in chiaro** sotto l'illustrazione (es. `LOB-EN005`, `MRD-IT060`) e un **passcode a 8 cifre** in basso a sinistra. Il codice set identifica esattamente la stampa (rarità + set), cosa che l'app Pokémon nel video deve far scegliere a mano. Con OCR del codice set la scelta della variante diventa automatica (fase 2).
- **Trappola 1:** la stessa illustrazione esiste in decine di ristampe con prezzi diversi da 0,05 € a centinaia di €. Il riconoscimento dell'illustrazione dà la carta, **non** la stampa. L'app deve mostrare il prezzo della stampa più comune come default onesto e lasciar cambiare stampa con un tap (come fa Acorn per N's Plan).
- **Trappola 2:** foil (Ultra/Secret/Prismatic) e riflessi rovinano gli hash: servono più frame consecutivi concordi prima di confermare.
- **Trappola 3:** carte Pendulum e Link hanno la cornice dell'illustrazione in posizione diversa: il ritaglio dell'artwork va adattato al tipo.
- **Prezzi:** per l'utente italiano il riferimento è **Cardmarket (€)**. YGOPRODeck espone il prezzo Cardmarket a livello di carta (il più basso) e il prezzo TCGplayer ($) per singola stampa. Il prezzo Cardmarket per singola stampa richiede l'API Cardmarket, non aperta: va detto chiaramente nell'app quale numero si sta guardando.
