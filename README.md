# 🃏 CrownCases.GG — Blackjack

A fully-featured, single-file browser blackjack game built for [CrownCases.GG](https://crowncases.gg). No dependencies, no build step — just drop `blackjack.html` in a browser and play.

---

## ✨ Features

### Core Gameplay
- **Standard Vegas Blackjack** — 6-deck shoe, dealer stands on soft 17 (configurable)
- **Hit, Stand, Double Down, Split, Surrender** — full action set
- **Blackjack pays 3:2**
- **Insurance** — offered when dealer shows an Ace; pays 2:1 if dealer has Blackjack
- **Provably Fair** — every shoe is seeded from a SHA-256 hash of a server seed + client seed + nonce, fully verifiable in-browser

### Split Hands
- Pairs split into **two independent hands displayed side by side**
- Active hand highlighted in **cyan** — inactive hand dims
- Each hand can **Hit, Stand, or Double** independently
- **Ace splits** auto-stand (one card each, no further action)
- Double on a split hand correctly charges an extra bet per hand and pays out independently

### Side Bets
Four side bets available, all lockable to auto-repeat each round:

| Bet | Top Payout |
|-----|-----------|
| 💎 **Perfect Pairs** — first 2 cards match by rank | Perfect Pair 25:1 · Coloured 12:1 · Mixed 6:1 |
| 🃏 **21+3** — your 2 cards + dealer up-card form a poker hand | Suited Trips 100:1 · Straight Flush 40:1 · Trips 30:1 · Straight 10:1 · Flush 5:1 |
| 👑 **Lucky Ladies** — first 2 cards total 20 | Q♥Q♥ 200:1 · Pair of Queens 25:1 · Any 20 4:1 |
| 🔥 **Blazing 7's** — hit three diamond 7s | 7♦7♦7♦ 500:1 |

- Side bet wins are **previewed instantly on deal** (toast appears as soon as cards land)
- Toast dismisses automatically when the player takes any action
- Side bets are included in the **total wager display**
- Locks persist across rounds; unlocked bets reset after each round

### UI / UX
- Dark casino aesthetic with **Orbitron + Rajdhani** typography
- Animated card dealing with configurable speed (Fast / Normal / Slow)
- **AI Basic Strategy Advisor** — highlights the recommended action button each hand
- Live **balance pill** in header, updates in real time
- **Round history** table in the sidebar (last 8 rounds)
- **Session stats modal** — rounds, wins, losses, pushes, win rate, net P/L, total wagered, RTP
- Bet controls (input, chips, ½ / 2× multipliers) and side bet inputs **lock during a round** and re-enable after
- Insufficient balance toast for invalid bet attempts

---

## 🚀 Getting Started

No installation required.

```bash
# Clone the repo
git clone https://github.com/your-username/crowncases-blackjack.git

# Open in browser
open blackjack.html
```

Or just download `blackjack.html` and open it directly — it's fully self-contained.

---

## 🎮 How to Play

1. **Set your bet** using the input field, chip buttons, or ½ / 2× multipliers
2. Optionally set **side bets** in the Side Bets tab — lock them to repeat every round
3. Click **DEAL** to start the round
4. Use **Hit / Stand / Double / Split / Surrender** to play your hand
5. If the dealer shows an **Ace**, you'll be prompted to take Insurance
6. Results and payouts are calculated automatically at the end of the round

---

## ⚙️ Settings

| Setting | Options |
|---------|---------|
| Card Animation Speed | Fast · Normal · Slow |
| AI Advisor | On / Off |
| Sound Effects | On / Off |
| Dealer Rules | Stand on Soft 17 · Hit on Soft 17 |

---

## 🔒 Provably Fair

Each round uses a **3-component seed**:

```
SHA-256(serverSeed : clientSeed : nonce)
```

- The **server seed** is hashed and committed before the round
- The **client seed** is randomly generated in-browser
- The **nonce** increments with every round
- After each session the previous server seed is **revealed** so you can verify any past round independently

Click **🔒 Provably Fair** in the header to inspect or verify your current round.

---

## 📁 Project Structure

```
blackjack.html   ← entire game (HTML + CSS + JS, single file)
README.md
```

---

## 🛠️ Tech Stack

- Vanilla HTML / CSS / JavaScript — zero dependencies
- Web Crypto API (`crypto.subtle`) for SHA-256 provably fair hashing
- Web Audio API for sound effects
- Google Fonts (Orbitron, Rajdhani, Inter) loaded via CDN

---

## 📜 License

MIT — free to use, modify, and deploy.
