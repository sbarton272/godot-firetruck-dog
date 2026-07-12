# godot-firetruck-dog
Firehuse dog drives the truck

## Running the project

This project uses git worktrees for feature branches, so each branch's code lives in its own
checkout on disk. Godot doesn't know about git branches directly — you open whichever
checkout's `project.godot` you want:

- `main` branch: this repo's root folder.
- A feature branch: its worktree folder, e.g. `.claude/worktrees/<branch-name>/`.

To open one: launch Godot → Project Manager → **Import** → point it at that folder's
`project.godot`. Each checkout shows up as its own entry in the Project Manager, so you can
have multiple branches open/tracked side by side.

### Testing scenes manually

- Open `scenes/Main.tscn` and press **F5** (or the Play button) to run the full game — it's
  set as the project's main scene.
- To test just the truck's driving physics in isolation (without the town), open
  `scenes/Truck.tscn` and press **F6** ("Run Current Scene") instead.
- Controls: **W/Up** throttle forward, **S/Down** reverse, **A/Left** / **D/Right** steer.
