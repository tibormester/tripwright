# tripwright
Tripwright is a lightweight AI-powered travel discovery prototype.

The goal is to let a user enter a destination or lodging area, discover nearby restaurants and attractions, select one, and receive a short AI-generated travel vignette with a supporting generated image.

## Getting started

backend is started with:
```
python backend/app.py
```
client is started with:
```
node client/client.js
```

## Design Decisions

- Server is not stateless, it is stateful. Facilitating more than one user at a time is not within the scope. 

