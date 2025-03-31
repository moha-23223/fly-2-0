from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import random
from typing import List
import random
from pydub import AudioSegment
from pydub.playback import play
from typing import List, Dict


GRID_SIZE = 5
direction_map = {
    (0, 1): "Right",
    (1, 0): "Down",
    (0, -1): "Left",
    (-1, 0): "Up"
}
direction_sounds = {
    "Right": "static/right.m4a",
    "Down": "static/down.m4a",
    "Left": "static/left.m4a",
    "Up": "static/up.m4a"}


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"),name="static")

game_state = {"status": "waiting","difficulty": "None"}

@app.get("/")
def home():
  return {"message": "Welcome to the fly Game!"}

@app.post("/play")
def play():
  game_state["status"] = "playing"
  return JSONResponse(content={"message": "game started","status":game_state["status"]})

@app.post("/settings")
def settings():
  return JSONResponse(content={"message": "Settings menu opened"})

@app.post("/exit")
def exit_game():
  game_state["status"] = "exited"
  return JSONResponse(content={"message": "Game exited", "status":game_state["status"]})

@app.post("/difficulty/{level}")
def set_difficulty(level: str):
  if level not in ["beginer", "experienced", "pro"]:
    return JSONResponse(content={"erroe": "invalid difficulty level"}, status_code=400)
  
  game_state["difficulty"] = level
  return JSONResponse(content={"message": f"difficulty set to {level}"})
  
def play_sound(direction: str):
    
    if direction in direction_sounds:
        audio = AudioSegment.from_file(direction_sounds[direction], format="m4a")
        play(audio)

def generate_non_repeating_route(steps: int) -> Dict[str, List]:
    
    start_x, start_y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
    route = [[start_x, start_y]]
    directions = [(0,1), (1,0), (0,-1), (-1,0)]  
    movement_directions = []
    audio_urls = []
    
    for _ in range(steps):
        possible_moves = []
        possible_dirs = []
        for dx, dy in directions:
            new_x, new_y = route[-1][0] + dx, route[-1][1] + dy
            
            
            if 0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE and [new_x, new_y] not in route:
                possible_moves.append((new_x, new_y))
                possible_dirs.append(direction_map[(dx, dy)])
        
        if not possible_moves:
            break 
        
        move_index = random.randint(0, len(possible_moves) - 1)
        next_move = possible_moves[move_index]
        route.append(list(next_move))
        direction = possible_dirs[move_index]
        movement_directions.append(direction)
        audio_urls.append(direction_sounds[direction])
    
    initial_position = route[0]
    final_position = route[-1]
    
    return {
        "initial_position": initial_position,
        "final_position": final_position,
        "route": route,
        "directions": movement_directions,
        "audio_urls": audio_urls
    }

@app.get("/fly_route/")
def get_fly_route(steps: int = 10):
    
    result = generate_non_repeating_route(steps)
    return result