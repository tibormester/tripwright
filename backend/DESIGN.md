# Tripwright MVP

Tripwright is a lightweight AI-powered travel discovery prototype.

The goal is to let a user enter a destination or lodging area, discover nearby restaurants and attractions, select one, and receive a short AI-generated travel vignette with a supporting generated image.

This is an on-rails, polished, multimodal travel exploration demo.

## Core Demo Goal

Build the fastest impressive MVP that shows:

- Real-world place discovery
- API-backed retrieval
- Simple agentic orchestration
- LLM-generated narrative output
- Image-generation prompt creation
- Clean, polished user experience

The app should feel like:

> “Enter a place. Pick a nearby experience. See the trip moment come to life.”

## MVP User Story

As a user, I can enter a location, hotel, neighborhood, or address.  
The app finds nearby restaurants and attractions.  
I pick one.  
The app generates a short cinematic travel vignette and a visual inspired by the place.

Example:

1. User enters: `Williamsburg, Brooklyn`
2. App finds nearby places:
   - Restaurants
   - Cafes
   - Parks
   - Attractions
   - Bars
3. User selects: `Domino Park`
4. App generates:
   - A title
   - A short prose scene
   - Practical details
   - A generated image prompt
   - Optional next stop suggestion

## Non-Goals

Do not build these for the MVP:

- Any enterprise features and complexity

This should be linear, reliable, and demo-friendly.

## Tech Stack


- Frontend: js
- Backend: Flask 
- Styling: Tailwind CSS
- Places API: Google Places API
- LLM: OpenAI
- Image generation: OpenAI image generation
- State: simple JSON objects

Choose the simplest stack that allows the demo to work end-to-end quickly.

## Primary Flow

### Step 1: User enters a location

Input examples:


Williamsburg Brooklyn
The Hoxton Chicago
Downtown Seattle
Near Pike Place Market
SoHo NYC

### Step 1.1: User Enters a vibe

Input exampls:

chill vacay
wild parties
romantic getaway

### Step 2: Location Agent discovers attractions in the area: restraunts and stuff.

### Step 3: Vibe Checker Agent filters and ranks the attractions to those that match the vibe best

### Step 4: Narrative Agent gives the user a story grounded in their selected location and offers them the filtered attractions

### Step 4.1: Painting Agent paints the scene using reference images and a textual prompt using the vibe

### Step 5: User describes what they want to do

### Step 6: Intent Parser agent maps user answer into a specifc attraction to visit first

### Repeat steps 4 through 6.