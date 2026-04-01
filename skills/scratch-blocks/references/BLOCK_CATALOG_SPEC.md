# Block Catalog Spec

## Fields

- `opcode`: Scratch opcode for this block template
- `shapes`: block shape tags
- `category`: Scratch category
- `text`: literal text segments
- `params`: param metadata and placeholder values
- `branch_labels`: labels for nested branches by index

Param items may contain:

- `type`: param kind such as `number`, `text`, or `dropdown`
- `value`: default value
- `options`: allowed values for dropdown-like params

Dropdown options by types:
- `dropdown`: options are difined on the block itself
- `dropdown-costume`: Costumes of the current sprite
- `dropdown-backdrop`: Backdrops of the stage
- `dropdown-sprite`: Sprites
- `dropdown-variable`: user self defined variables
- `dropdown-list`: user self defined list variables
- `dropdown-key`: keyboard keys, 0-9, a-z, arrow keys, space, any
- `dropdown-timeunit`: year, month, day, hour, minute, second
- `dropdown-color`: colors
- `dropdown-mathop`: abs, floor, celling, sqrt, sin, cos, tan, asin, acos, atan, ln, log, e^, 10^
- `dropdown-position`: random, mouse pointer
- `dropdown-sound`: sounds
- `dropdown-broadcast-message`: broadcast messages
- `dropdown-touch`: mouse pointer, edge
