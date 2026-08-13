# Legacy migration

The repository history is retained, but root-level legacy scripts are not the
recommended runtime path. They include blocking sleep-based motion and an unsafe
text-to-`exec` control interface. New work belongs in `turtlebot3_multimodal/`.

| Legacy path | Replacement |
|---|---|
| `/chatter` Python source text | `/turtlebot3/command` validated JSON |
| `exec(msg.data)` | strict parser and action whitelist |
| blocking movement loops | timer-driven `MotionExecutor` |
| hard-coded rosbridge address | ROS-native local command topic |
| model-generated Python | model-generated JSON only |
| no emergency-stop state | latched stop/reset services and watchdog |

The previous MediaPipe task file and legacy scripts remain recoverable from the
`main` branch and repository history but are removed from this upgrade branch.
The task model is not required by the safe core; a later perception phase will
use a documented download and checksum workflow instead of committing binaries.
