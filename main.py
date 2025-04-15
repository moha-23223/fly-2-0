import random
import os
import gettext
import logging
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from lti import ToolProvider
from lti.outcome_request import OutcomeRequest

# Settings
GRID_SIZE = 5
CONSUMER_KEY = "your_moodle_key"
CONSUMER_SECRET = "your_moodle_secret"
LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")

# Direction data
direction_map = {(0, 1): "Right", (1, 0): "Down", (0, -1): "Left", (-1, 0): "Up"}
direction_sounds = {
    "Right": "static/right.m4a",
    "Down": "static/down.m4a",
    "Left": "static/left.m4a",
    "Up": "static/up.m4a"
}

# Initialize app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/scorm", StaticFiles(directory="static/scorm"), name="scorm")
logging.basicConfig(filename="logs/activity.log", level=logging.INFO)

# Game state
game_state = {
    "status": "waiting",
    "difficulty": "None",
    "score": 0,
    "path": None
}


# Localization
def get_translator(lang_code: str):
    try:
        translator = gettext.translation('messages', localedir=LOCALES_DIR, languages=[lang_code])
        return translator.gettext
    except FileNotFoundError:
        return lambda s: s

@app.middleware("http")
async def add_gettext_to_request(request: Request, call_next):
    lang = request.headers.get("Accept-Language", "ru").split(',')[0]
    request.state._ = get_translator(lang)
    return await call_next(request)

# Routes
@app.get("/")
def root(request: Request):
    _ = request.state._
    return {"message": _("SCORM server running. Access at /scorm/content/index.html")}

@app.post("/play")
def play_game(steps: int = 10):
    game_state["status"] = "playing"
    game_state["score"] = 0  # reset score
    game_state["path"] = generate_non_repeating_route(steps)
    return JSONResponse(content={
        "message": "game started",
        "status": game_state["status"],
        "path": game_state["path"]
    })


@app.post("/settings")
def settings():
    return JSONResponse(content={"message": "Settings menu opened"})

@app.post("/exit")
def exit_game():
    game_state["status"] = "exited"
    return JSONResponse(content={"message": "Game exited", "status": game_state["status"]})

@app.post("/difficulty/{level}")
def set_difficulty(level: str):
    if level not in ["beginner", "experienced", "pro"]:
        return JSONResponse(content={"error": "invalid difficulty level"}, status_code=400)
    game_state["difficulty"] = level
    return JSONResponse(content={"message": f"difficulty set to {level}"})

@app.get("/fly_route/")
def get_fly_route(steps: int = 10):
    return generate_non_repeating_route(steps)

def generate_non_repeating_route(steps: int) -> dict:
    start_x, start_y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
    route = [[start_x, start_y]]
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
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

    return {
        "initial_position": route[0],
        "final_position": route[-1],
        "route": route,
        "directions": movement_directions,
        "audio_urls": audio_urls
    }

@app.post("/lti/launch")
async def lti_launch(request: Request):
    form_data = await request.form()
    tool_provider = ToolProvider(CONSUMER_KEY, CONSUMER_SECRET, dict(form_data))

    if not tool_provider.is_valid_request(request):
        return JSONResponse(status_code=400, content={"error": "Invalid LTI request"})

    return {
        "message": "LTI launch successful",
        "user_id": form_data.get("user_id"),
        "lis_result_sourcedid": form_data.get("lis_result_sourcedid"),
        "lis_outcome_service_url": form_data.get("lis_outcome_service_url"),
    }

@app.post("/lti/submit_score")
async def submit_score(
    lis_result_sourcedid: str = Form(...),
    lis_outcome_service_url: str = Form(...),
    score: float = Form(...)
):
    normalized_score = score / 100.0
    tool_provider = ToolProvider(CONSUMER_KEY, CONSUMER_SECRET, {})
    outcome_request = OutcomeRequest()
    outcome_request.consumer_key = CONSUMER_KEY
    outcome_request.consumer_secret = CONSUMER_SECRET
    outcome_request.lis_outcome_service_url = lis_outcome_service_url
    outcome_request.lis_result_sourcedid = lis_result_sourcedid
    outcome_request.score = normalized_score
    response = outcome_request.post_replace_result()

    if response.is_success():
        return {"message": "Score sent to Moodle successfully"}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to send score to Moodle"})

@app.get("/scorm/track")
async def track_data(request: Request):
    data = await request.json()
    logging.info(f"SCORM Data: {data}")
    return JSONResponse(content={"status": "ok"})



@app.post("/score")
async def update_score(score: int = Form(...)):
    game_state["score"] = score
    return JSONResponse(content={"message": "score updated", "score": game_state["score"]})
@app.get("/game/state")
def get_game_state():
    return {
        "status": game_state["status"],
        "difficulty": game_state["difficulty"],
        "score": game_state["score"],
        "path": game_state["path"]
    }
