# osu2saber

Convert beatmaps from the `Songs` folder from osu! into `CustomLevels` folder from Beat Saber.

## Playability
Expect unnatural movements from mouse and tablet (a direct and often exagerated translation from osu motions) and note overload (mostly dot boxes) on BSaber.

## Requirements
 - Python
 - Pillow (Python Imaging Library)
 - ffmpeg (in PATH)

## Usage
### Single beatmap
`python -m osu2saber <BEATMAPSET_FOLDER> <CUSTOMLEVELS_FOLDER>`

e.g.:

`python -m osu2saber ~/".osu/Songs/1040733 LukHash - SOCIAL PHOBIA" ~/".local/share/Steam/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels"`

### All beatmaps
`python -m osu2saber --songs <OSU_SONGS_FOLDER> <CUSTOMLEVELS_FOLDER>`

e.g.:

`python -m osu2saber --songs ~/.osu/Songs ~/".local/share/Steam/steamapps/common/Beat Saber/Beat Saber_Data/CustomLevels"`

