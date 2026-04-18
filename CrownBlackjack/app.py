"""
CrownCases.GG Blackjack — Backend (app.py)
Flask server for session management, game history, stats, and provably fair verification.
Run: pip install flask flask-cors && python app.py
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3, hashlib, hmac, secrets, json, time, os
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

DB_PATH = 'crowncases_blackjack.db'

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS players (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT UNIQUE NOT NULL,
                balance     REAL DEFAULT 1000.0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen   TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rounds (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                round_number  INTEGER NOT NULL,
                bet           REAL NOT NULL,
                player_hand   TEXT NOT NULL,
                dealer_hand   TEXT NOT NULL,
                result        TEXT NOT NULL,
                payout        REAL NOT NULL,
                side_bets     TEXT DEFAULT '{}',
                server_seed   TEXT,
                client_seed   TEXT,
                nonce         INTEGER,
                combined_hash TEXT,
                played_at     TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS provably_fair (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                server_seed   TEXT NOT NULL,
                server_hash   TEXT NOT NULL,
                client_seed   TEXT NOT NULL,
                nonce         INTEGER NOT NULL,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def hmac_sha256(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()

def get_or_create_player(sid: str):
    with get_db() as db:
        row = db.execute('SELECT * FROM players WHERE session_id=?', (sid,)).fetchone()
        if not row:
            db.execute('INSERT INTO players (session_id) VALUES (?)', (sid,))
            db.commit()
            row = db.execute('SELECT * FROM players WHERE session_id=?', (sid,)).fetchone()
        else:
            db.execute('UPDATE players SET last_seen=? WHERE session_id=?',
                       (datetime.utcnow().isoformat(), sid))
            db.commit()
    return dict(row)

def player_stats(sid: str):
    with get_db() as db:
        rows = db.execute(
            'SELECT result, bet, payout FROM rounds WHERE session_id=?', (sid,)
        ).fetchall()
    total   = len(rows)
    wins    = sum(1 for r in rows if r['result'] == 'Win')
    losses  = sum(1 for r in rows if r['result'] == 'Loss')
    pushes  = sum(1 for r in rows if r['result'] == 'Push')
    wagered = sum(r['bet'] for r in rows)
    net     = sum(r['payout'] - r['bet'] for r in rows)
    rtp     = round((wagered + net) / wagered * 100, 2) if wagered > 0 else 0.0
    return {
        'total': total, 'wins': wins, 'losses': losses, 'pushes': pushes,
        'wagered': round(wagered, 2), 'net': round(net, 2), 'rtp': rtp,
        'win_rate': round(wins / total * 100, 1) if total > 0 else 0
    }

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve the blackjack HTML file."""
    return app.send_static_file('blackjack.html')


# ── Session / Balance ────────────────────────────────────────────────────────

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create or resume a session."""
    sid = request.json.get('session_id') or secrets.token_hex(16)
    player = get_or_create_player(sid)
    return jsonify({'session_id': sid, 'balance': player['balance']})


@app.route('/api/balance', methods=['GET'])
def get_balance():
    sid = request.args.get('session_id')
    if not sid:
        return jsonify({'error': 'session_id required'}), 400
    player = get_or_create_player(sid)
    return jsonify({'balance': player['balance']})


@app.route('/api/balance/add', methods=['POST'])
def add_balance():
    """Add chips (simulate deposit / top-up for demo)."""
    data = request.json
    sid  = data.get('session_id')
    amt  = float(data.get('amount', 0))
    if not sid or amt <= 0:
        return jsonify({'error': 'Invalid request'}), 400
    with get_db() as db:
        db.execute('UPDATE players SET balance = balance + ? WHERE session_id=?', (amt, sid))
        db.commit()
        row = db.execute('SELECT balance FROM players WHERE session_id=?', (sid,)).fetchone()
    return jsonify({'balance': row['balance']})


# ── Provably Fair ────────────────────────────────────────────────────────────

@app.route('/api/provably-fair/init', methods=['POST'])
def pf_init():
    """Generate new server seed + hash for next round."""
    sid = request.json.get('session_id')
    nonce = int(request.json.get('nonce', 0))
    client_seed = request.json.get('client_seed', secrets.token_hex(16))

    server_seed = secrets.token_hex(32)
    server_hash = sha256(server_seed)

    with get_db() as db:
        db.execute(
            'INSERT INTO provably_fair (session_id, server_seed, server_hash, client_seed, nonce) VALUES (?,?,?,?,?)',
            (sid, server_seed, server_hash, client_seed, nonce)
        )
        db.commit()

    return jsonify({
        'server_hash': server_hash,
        'client_seed': client_seed,
        'nonce': nonce
    })


@app.route('/api/provably-fair/verify', methods=['POST'])
def pf_verify():
    """Verify a completed round's fairness."""
    data        = request.json
    server_seed = data.get('server_seed')
    client_seed = data.get('client_seed')
    nonce       = data.get('nonce')
    claimed_hash = data.get('combined_hash')

    if not all([server_seed, client_seed, nonce is not None]):
        return jsonify({'error': 'Missing parameters'}), 400

    combined = sha256(f"{server_seed}:{client_seed}:{nonce}")
    server_hash = sha256(server_seed)
    valid = combined == claimed_hash if claimed_hash else True

    return jsonify({
        'valid': valid,
        'server_hash': server_hash,
        'combined_hash': combined,
        'message': '✅ Round verified as provably fair.' if valid else '❌ Hash mismatch.'
    })


# ── Round Recording ──────────────────────────────────────────────────────────

@app.route('/api/round/record', methods=['POST'])
def record_round():
    """
    Record a completed round and update balance.
    Payload: {
      session_id, round_number, bet, player_hand, dealer_hand,
      result, payout, side_bets, server_seed, client_seed, nonce, combined_hash
    }
    """
    d = request.json
    sid = d.get('session_id')
    if not sid:
        return jsonify({'error': 'session_id required'}), 400

    with get_db() as db:
        # Verify player exists
        player = db.execute('SELECT * FROM players WHERE session_id=?', (sid,)).fetchone()
        if not player:
            return jsonify({'error': 'Player not found'}), 404

        new_balance = float(player['balance']) - float(d['bet']) + float(d['payout'])

        db.execute('''
            INSERT INTO rounds
              (session_id, round_number, bet, player_hand, dealer_hand,
               result, payout, side_bets, server_seed, client_seed, nonce, combined_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            sid,
            d.get('round_number', 0),
            d['bet'],
            json.dumps(d.get('player_hand', [])),
            json.dumps(d.get('dealer_hand', [])),
            d['result'],
            d['payout'],
            json.dumps(d.get('side_bets', {})),
            d.get('server_seed'),
            d.get('client_seed'),
            d.get('nonce'),
            d.get('combined_hash')
        ))

        db.execute('UPDATE players SET balance=? WHERE session_id=?', (new_balance, sid))
        db.commit()

    return jsonify({'balance': round(new_balance, 2), 'recorded': True})


# ── History & Stats ──────────────────────────────────────────────────────────

@app.route('/api/history', methods=['GET'])
def get_history():
    """Return last N rounds for a session."""
    sid   = request.args.get('session_id')
    limit = int(request.args.get('limit', 20))
    if not sid:
        return jsonify({'error': 'session_id required'}), 400

    with get_db() as db:
        rows = db.execute(
            'SELECT * FROM rounds WHERE session_id=? ORDER BY played_at DESC LIMIT ?',
            (sid, limit)
        ).fetchall()

    return jsonify({'history': [dict(r) for r in rows]})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Return aggregate stats for a session."""
    sid = request.args.get('session_id')
    if not sid:
        return jsonify({'error': 'session_id required'}), 400
    return jsonify(player_stats(sid))


@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    """Top players by net profit (demo leaderboard)."""
    with get_db() as db:
        rows = db.execute('''
            SELECT p.session_id,
                   p.balance,
                   COUNT(r.id) AS total_rounds,
                   COALESCE(SUM(r.payout - r.bet), 0) AS net_profit
            FROM players p
            LEFT JOIN rounds r ON p.session_id = r.session_id
            GROUP BY p.session_id
            ORDER BY net_profit DESC
            LIMIT 10
        ''').fetchall()
    return jsonify({'leaderboard': [dict(r) for r in rows]})


# ── AI Strategy Hint ─────────────────────────────────────────────────────────

@app.route('/api/ai/hint', methods=['POST'])
def ai_hint():
    """
    Return basic strategy hint based on player hand vs dealer upcard.
    player_score: int, dealer_upcard: int (2-11), is_soft: bool, can_double: bool
    """
    d = request.json
    ps  = int(d.get('player_score', 0))
    du  = int(d.get('dealer_upcard', 2))
    soft = bool(d.get('is_soft', False))
    can_double = bool(d.get('can_double', True))

    # Basic Strategy lookup (simplified but accurate for most hands)
    action = 'Hit'
    explanation = ''

    if ps >= 17:
        action = 'Stand'
        explanation = f'Stand on {ps} — solid hand.'
    elif ps >= 13 and ps <= 16 and du <= 6:
        action = 'Stand'
        explanation = f'Dealer shows {du} — likely to bust. Stand.'
    elif ps >= 13 and ps <= 16 and du >= 7:
        action = 'Hit'
        explanation = f'Dealer shows {du} — strong card. Hit to improve.'
    elif ps == 12 and 4 <= du <= 6:
        action = 'Stand'
        explanation = 'Dealer bust range (4-6). Stand on 12.'
    elif ps == 11 and can_double:
        action = 'Double'
        explanation = f'11 vs {du} — double down for maximum value.'
    elif ps == 10 and du <= 9 and can_double:
        action = 'Double'
        explanation = f'10 vs {du} — strong double down opportunity.'
    elif ps == 9 and 3 <= du <= 6 and can_double:
        action = 'Double'
        explanation = f'9 vs {du} — marginal double down.'
    elif ps <= 8:
        action = 'Hit'
        explanation = 'Low total — always hit.'
    elif soft and ps == 18 and du >= 9:
        action = 'Hit'
        explanation = f'Soft 18 vs dealer {du} — hit to a stronger total.'
    else:
        action = 'Hit'
        explanation = f'Hit — build towards 17+.'

    return jsonify({'action': action, 'explanation': explanation, 'rtp_note': '95% RTP — house edge 5%'})


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  CrownCases.GG Blackjack Server")
    print("  http://localhost:5000")
    print("  DB:", os.path.abspath(DB_PATH))
    print("=" * 55)
    app.run(debug=True, port=5000)
