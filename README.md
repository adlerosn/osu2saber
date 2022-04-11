# osu2saber

Convert beatmaps from the `Songs` folder from osu! into `CustomLevels` folder from Beat Saber.

## Playability
Expect pre-alpha conversion quality.

## Requirements
 - Python
 - Pillow (Python Imaging Library)
 - ffmpeg (in PATH)

## Usage
### Single beatmap
`./osu2saber.py <BEATMAPSET_FOLDER> <CUSTOMLEVELS_FOLDER>`

e.g.:

`./osu2saber.py ~/".osu/Songs/1040733 LukHash - SOCIAL PHOBIA" ~/".local/share/Steam/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels"`

### All beatmaps
`./osu2saber.py --songs <OSU_SONGS_FOLDER> <CUSTOMLEVELS_FOLDER>`

e.g.:

`./osu2saber.py --songs ~/.osu/Songs ~/".local/share/Steam/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels"`

