# 🔴 Real-time avec FastAPI - Options Disponibles

## 📋 Comparaison Supabase vs FastAPI

| Fonctionnalité | Supabase | FastAPI |
|----------------|----------|---------|
| **Real-time natif** | ✅ Oui (PostgreSQL Realtime) | ❌ Non |
| **WebSockets** | ✅ Oui | ✅ Oui (natif) |
| **Server-Sent Events** | ✅ Oui | ✅ Oui (natif) |
| **Subscriptions automatiques** | ✅ Oui (basé sur RLS) | ❌ Non (à implémenter) |

---

## 🚀 Solutions Disponibles

### 1. **WebSockets Natifs FastAPI** (Recommandé)

**Avantages** :
- ✅ Intégré dans FastAPI
- ✅ Pas de dépendance externe
- ✅ Contrôle total
- ✅ Performant

**Inconvénients** :
- ❌ Pas de subscriptions automatiques (à gérer manuellement)
- ❌ Pas de gestion automatique des reconnexions côté client

**Exemple d'implémentation** :

```python
# app/api/v1/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Traiter les messages entrants
            await manager.broadcast({"message": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Usage côté frontend** :
```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Nouveau message:', data);
};
```

---

### 2. **Server-Sent Events (SSE)** 

**Avantages** :
- ✅ Simple à implémenter
- ✅ Reconnexion automatique côté client
- ✅ Unidirectionnel (serveur → client)

**Inconvénients** :
- ❌ Unidirectionnel seulement (pas de messages client → serveur)
- ❌ Moins performant que WebSockets pour beaucoup de connexions

**Exemple** :

```python
# app/api/v1/sse.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

async def event_generator():
    while True:
        # Vérifier les changements dans la base de données
        # (polling ou utiliser PostgreSQL LISTEN/NOTIFY)
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'message': 'update'})}\n\n"

@router.get("/events")
async def stream_events():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Usage côté frontend** :
```typescript
const eventSource = new EventSource('http://localhost:8000/api/v1/events');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

---

### 3. **PostgreSQL LISTEN/NOTIFY + WebSockets** (Meilleur pour DB changes)

**Avantages** :
- ✅ Réactif aux changements réels dans PostgreSQL
- ✅ Pas de polling nécessaire
- ✅ Efficace

**Inconvénients** :
- ❌ Plus complexe à mettre en place
- ❌ Nécessite des triggers PostgreSQL ou application-level notifications

**Exemple** :

```python
# app/core/realtime.py
import asyncio
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.database.base import engine
from app.models.patient import PatientTreatment

class RealtimeManager:
    def __init__(self):
        self.connections: List[WebSocket] = []
        self.setup_listeners()
    
    def setup_listeners(self):
        # Écouter les changements dans la base de données
        @event.listens_for(PatientTreatment, 'after_insert')
        def receive_after_insert(mapper, connection, target):
            asyncio.create_task(self.broadcast({
                'event': 'INSERT',
                'table': 'patient_treatments',
                'data': {'id': str(target.id)}
            }))
        
        @event.listens_for(PatientTreatment, 'after_update')
        def receive_after_update(mapper, connection, target):
            asyncio.create_task(self.broadcast({
                'event': 'UPDATE',
                'table': 'patient_treatments',
                'data': {'id': str(target.id)}
            }))
    
    async def broadcast(self, message: dict):
        for ws in self.connections:
            await ws.send_json(message)
```

---

### 4. **Socket.IO avec python-socketio** (Alternative complète)

**Avantages** :
- ✅ Reconnexion automatique
- ✅ Rooms/Channels (comme Supabase)
- ✅ Fallback vers polling si WebSocket échoue
- ✅ Compatible avec Socket.IO côté client

**Inconvénients** :
- ❌ Dépendance externe
- ❌ Plus lourd

**Installation** :
```bash
pip install python-socketio uvicorn[standard]
```

**Exemple** :
```python
import socketio

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"Client connecté: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client déconnecté: {sid}")

@sio.event
async def subscribe(sid, data):
    room = data.get('room')
    sio.enter_room(sid, room)
    await sio.emit('subscribed', {'room': room}, room=sid)
```

---

## 🎯 Recommandation pour Move4Epilepsy

### Pour remplacer Supabase Realtime :

**Option recommandée** : **WebSockets natifs + PostgreSQL LISTEN/NOTIFY**

**Pourquoi** :
- ✅ Pas de dépendance externe
- ✅ Performant
- ✅ Réactif aux changements réels dans PostgreSQL
- ✅ Contrôle total sur les permissions

**Cas d'usage** :
1. **Chat en temps réel** : WebSockets pour les messages
2. **Notifications de stock** : LISTEN/NOTIFY quand un stock change
3. **Alertes patients** : SSE pour les alertes de disponibilité
4. **Dashboard admin** : WebSockets pour les stats en temps réel

---

## 📝 Exemple Complet : Chat Real-time

```python
# app/api/v1/chat_realtime.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.security import get_current_user_optional
from app.models.user import User

router = APIRouter()

class ChatManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}  # channel_id -> [websockets]
    
    async def connect(self, websocket: WebSocket, channel_id: str):
        await websocket.accept()
        if channel_id not in self.connections:
            self.connections[channel_id] = []
        self.connections[channel_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, channel_id: str):
        if channel_id in self.connections:
            self.connections[channel_id].remove(websocket)
    
    async def broadcast_to_channel(self, channel_id: str, message: dict):
        if channel_id in self.connections:
            for connection in self.connections[channel_id]:
                await connection.send_json(message)

chat_manager = ChatManager()

@router.websocket("/chat/{channel_id}/ws")
async def chat_websocket(websocket: WebSocket, channel_id: str):
    await chat_manager.connect(websocket, channel_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Sauvegarder le message dans la DB
            # Puis diffuser aux autres clients
            await chat_manager.broadcast_to_channel(channel_id, {
                'type': 'message',
                'data': data
            })
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, channel_id)
```

---

## 🔄 Migration depuis Supabase Realtime

**Avant (Supabase)** :
```typescript
const channel = supabase
  .channel('patient_treatments')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'patient_treatments'
  }, (payload) => {
    console.log('Nouveau traitement:', payload.new);
  })
  .subscribe();
```

**Après (FastAPI WebSockets)** :
```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/realtime/patient_treatments');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.event === 'INSERT') {
    console.log('Nouveau traitement:', data.data);
  }
};
```

---

## ⚙️ Configuration Recommandée

1. **Pour le chat** : WebSockets natifs FastAPI
2. **Pour les notifications** : Server-Sent Events (SSE)
3. **Pour les changements DB** : PostgreSQL LISTEN/NOTIFY + WebSockets
4. **Pour la compatibilité maximale** : Socket.IO

---

## 📚 Ressources

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Server-Sent Events](https://fastapi.tiangolo.com/advanced/server-sent-events/)
- [PostgreSQL LISTEN/NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)
- [python-socketio](https://python-socketio.readthedocs.io/)

---

**✅ Conclusion** : Oui, on peut faire du real-time avec FastAPI, mais il faut l'implémenter manuellement. Les WebSockets natifs sont la solution la plus simple et performante.
