#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from enum import IntEnum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

'''https://bsmg.wiki/mapping/map-format.html'''


class BeatSaberInfoButDifficulties:
    def __init__(self,
                 songName: str = '',
                 songSubName: str = '',
                 songAuthorName: str = '',
                 levelAuthorName: str = '',
                 beatsPerMinute: float = 150.00,
                 previewStartTime: float = 20.25,
                 previewDuration: float = 10.00,
                 customData: Dict[str, Any] = None
                 ) -> None:
        self.version = '2.0.0'
        self.songName = songName
        self.songSubName = songSubName
        self.songAuthorName = songAuthorName
        self.levelAuthorName = levelAuthorName
        self.beatsPerMinute = beatsPerMinute
        # 4/4 timing is HARDCODED on BeatSaber side
        self._msBetweenTimePoints: float = 60000/(4*self.beatsPerMinute)
        self.shuffle = 0
        self.shufflePeriod = 0.5
        self.previewStartTime = previewStartTime
        self.previewDuration = previewDuration
        self.songFilename = 'song.egg'
        self.coverImageFilename = 'cover.jpg'
        self.environmentName = 'DefaultEnvironment'
        self.allDirectionsEnvironmentName = 'DefaultEnvironment'
        self.songTimeOffset = 0
        self.customData: Dict[str, Any] = customData or dict()
        self.difficultyBeatmapSets: list = list()

    def round_to_beat(self, event_ms: Union[int, float]) -> int:
        return round(round(event_ms/self._msBetweenTimePoints)*self._msBetweenTimePoints)

    def convert_to_beat(self, event_ms: Union[int, float]) -> float:
        return self.round_to_beat(event_ms)/(self._msBetweenTimePoints*4)

    def with_song_sub_name(self, songSubName: str) -> 'BeatSaberInfoButDifficulties':
        return type(self)(
            self.songName,
            songSubName,
            self.songAuthorName,
            self.levelAuthorName,
            self.beatsPerMinute,
            self.previewStartTime,
            self.previewDuration,
            self.customData,
        )

    def with_difficulties(self, difficultyBeatmapSets: List['BeatSaberDifficultyV260']) -> 'BeatSaberInfo':
        return BeatSaberInfo(
            self.songName,
            self.songSubName,
            self.songAuthorName,
            self.levelAuthorName,
            self.beatsPerMinute,
            self.previewStartTime,
            self.previewDuration,
            self.customData,
            difficultyBeatmapSets,
        )


class BeatSaberInfo(BeatSaberInfoButDifficulties):
    def __init__(self,
                 songName: str = '',
                 songSubName: str = '',
                 songAuthorName: str = '',
                 levelAuthorName: str = '',
                 beatsPerMinute: float = 150.00,
                 previewStartTime: float = 20.25,
                 previewDuration: float = 10.00,
                 customData: Dict[str, Any] = None,
                 difficultyBeatmapSets: List['BeatSaberDifficultyV260'] = None,
                 ) -> None:
        super().__init__(
            songName,
            songSubName,
            songAuthorName,
            levelAuthorName,
            beatsPerMinute,
            previewStartTime,
            previewDuration,
            customData,
        )
        self.difficultyBeatmapSets: List['BeatSaberDifficultyV260'] = (
            difficultyBeatmapSets or list())
        self._difficulty_internals = BeatSaberDifficultyEnum.pick(
            len(self.difficultyBeatmapSets))

    def to_jsonable(self) -> dict:
        return {
            "_version": self.version,
            "_songName": self.songName,
            "_songSubName": self.songSubName,
            "_songAuthorName": self.songAuthorName,
            "_levelAuthorName": self.levelAuthorName,
            "_beatsPerMinute": self.beatsPerMinute,
            "_shuffle": self.shuffle,
            "_shufflePeriod": self.shufflePeriod,
            "_previewStartTime": self.previewStartTime,
            "_previewDuration": self.previewDuration,
            "_songFilename": self.songFilename,
            "_coverImageFilename": self.coverImageFilename,
            "_environmentName": self.environmentName,
            "_allDirectionsEnvironmentName": self.allDirectionsEnvironmentName,
            "_songTimeOffset": self.songTimeOffset,
            **(dict() if len(self.customData) <= 0 else dict(_customData=self.customData)),
            "_difficultyBeatmapSets": [
                {
                    "_beatmapCharacteristicName": "Standard",
                    "_difficultyBeatmaps": [
                        {
                            "_difficulty": di.name,
                            "_difficultyRank": di.value,
                            "_beatmapFilename": f"Standard{di.name}.dat",
                            "_noteJumpMovementSpeed": 10,
                            "_noteJumpStartBeatOffset": 0,
                            "_customData": {
                                "_difficultyLabel": df.difficulty_label,
                                "_editorOffset": 0,
                                "_editorOldOffset": 0,
                                ** df.customData
                            }
                        }
                        for di, df in zip(self._difficulty_internals, self.difficultyBeatmapSets)
                    ]
                }
            ]
        }

    def write_to(self, path: Path):
        path.joinpath('Info.dat').write_text(json.dumps(
            self.to_jsonable(), ensure_ascii=False, indent=2), encoding='utf-8')
        for di, df in zip(self._difficulty_internals, self.difficultyBeatmapSets):
            path.joinpath(f"Standard{di.name}.dat").write_text(json.dumps(
                df.to_jsonable(), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


class BeatSaberDifficultyEnum(IntEnum):
    Easy = 1
    Normal = 3
    Hard = 5
    Expert = 7
    ExpertPlus = 9

    @classmethod
    def pick(cls, qtty: int) -> List['BeatSaberDifficultyEnum']:
        if qtty < 1 or qtty > 5:
            raise ValueError(f'{qtty=} must be in the range [1, 5]')
        return [
            [cls.Hard],
            [cls.Normal, cls.Hard],
            [cls.Normal, cls.Hard, cls.Expert],
            [cls.Easy, cls.Normal, cls.Hard, cls.Expert],
            [cls.Easy, cls.Normal, cls.Hard, cls.Expert, cls.ExpertPlus],
        ][qtty-1]


class BeatSaberDifficultyV260:
    def __init__(self,
                 ) -> None:
        self.version = '2.6.0'
        self.notes: List[BeatSaberDifficultyNote] = list()
        self.sliders: List[BeatSaberDifficultySlider] = list()
        self.obstacles: List[BeatSaberDifficultyObstacle] = list()
        self.events: List[Any] = list()
        self.waypoints: List[Any] = list()
        self.difficulty_label: str = 'Normal'
        self.customData: Dict[str, Any] = dict()

    def to_jsonable(self) -> dict:
        return {
            "_version": self.version,
            "_notes": list(map(BeatSaberDifficultyNote.to_jsonable, self.notes)),
            "_sliders": list(map(BeatSaberDifficultySlider.to_jsonable, self.sliders)),
            "_obstacles": list(map(BeatSaberDifficultyObstacle.to_jsonable, self.obstacles)),
            "_events": self.events,
            "_waypoints": self.waypoints,
        }


class BeatSaberDifficultyNote:
    def __init__(self,
                 time,
                 lineIndex,
                 lineLayer,
                 type_,
                 cutDirection,
                 ) -> None:
        self.time: float = time
        self.lineIndex: int = lineIndex
        self.lineLayer: int = lineLayer
        self.type: int = type_
        self.cutDirection: int = cutDirection

    def to_jsonable(self) -> dict:
        return {
            "_time": self.time,
            "_lineIndex": self.lineIndex,
            "_lineLayer": self.lineLayer,
            "_type": self.type,
            "_cutDirection": self.cutDirection,
        }


class BeatSaberDifficultySlider:
    def __init__(self,
                 colorType: 'NoteTypeEnum',
                 headTime: float,
                 headLineIndex: 'NoteLineIndexEnum',
                 headLineLayer: 'NoteLineLayerEnum',
                 headControlPointLengthMultiplier: float,
                 headCutDirection: 'NoteCutDirectionEnum',
                 tailTime: float,
                 tailLineIndex: 'NoteLineIndexEnum',
                 tailLineLayer: 'NoteLineLayerEnum',
                 tailControlPointLengthMultiplier: float,
                 tailCutDirection: 'NoteCutDirectionEnum',
                 sliderMidAnchorMode: 'SliderMidAnchorModeEnum',
                 ) -> None:
        self.colorType: NoteTypeEnum = colorType
        self.headTime: float = headTime
        self.headLineIndex: NoteLineIndexEnum = headLineIndex
        self.headLineLayer: NoteLineLayerEnum = headLineLayer
        self.headControlPointLengthMultiplier: float = headControlPointLengthMultiplier
        self.headCutDirection: NoteCutDirectionEnum = headCutDirection
        self.tailTime: float = tailTime
        self.tailLineIndex: NoteLineIndexEnum = tailLineIndex
        self.tailLineLayer: NoteLineLayerEnum = tailLineLayer
        self.tailControlPointLengthMultiplier: float = tailControlPointLengthMultiplier
        self.tailCutDirection: NoteCutDirectionEnum = tailCutDirection
        self.sliderMidAnchorMode: SliderMidAnchorModeEnum = sliderMidAnchorMode

    def to_jsonable(self) -> dict:
        return {
            "_colorType": self.colorType,
            "_headTime": self.headTime,
            "_headLineIndex": self.headLineIndex,
            "_headLineLayer": self.headLineLayer,
            "_headControlPointLengthMultiplier": self.headControlPointLengthMultiplier,
            "_headCutDirection": self.headCutDirection,
            "_tailTime": self.tailTime,
            "_tailLineIndex": self.tailLineIndex,
            "_tailLineLayer": self.tailLineLayer,
            "_tailControlPointLengthMultiplier": self.tailControlPointLengthMultiplier,
            "_tailCutDirection": self.tailCutDirection,
            "_sliderMidAnchorMode": self.sliderMidAnchorMode,
        }


class BeatSaberDifficultyObstacleTypeEnum(IntEnum):
    FullHeightWall = 0
    CrouchWall = 1


class BeatSaberDifficultyObstacle:
    def __init__(self,
                 time: float,
                 lineIndex: int,
                 type: BeatSaberDifficultyObstacleTypeEnum,
                 duration: float,
                 width: int,
                 ) -> None:
        self.time: float = time
        self.lineIndex: int = lineIndex
        self.type: BeatSaberDifficultyObstacleTypeEnum = type
        self.duration: float = duration
        self.width: int = width

    def to_jsonable(self) -> dict:
        return {
            "_time": self.time,
            "_lineIndex": self.lineIndex,
            "_type": self.type,
            "_duration": self.duration,
            "_width": self.width,
        }


class SliderMidAnchorModeEnum(IntEnum):
    Straight = 0
    Clockwise = 1
    CounterClockwise = 2


class NoteLineIndexEnum(IntEnum):
    '''Bottom-left origin'''
    OffLeft = -1
    FarLeft = 0
    LightLeft = 1
    LightRight = 2
    FarRight = 3
    OffRight = 4


class NoteLineLayerEnum(IntEnum):
    '''Bottom-left origin'''
    OffBottom = -1
    Bottom = 0
    Middle = 1
    Top = 2
    OffTop = 3


class NoteTypeEnum(IntEnum):
    LeftRedNote = 0
    RightBlueNote = 1
    Unused = 2
    Bomb = 3


class NoteCutDirectionEnum(IntEnum):
    Up = 0
    Down = 1
    Left = 2
    Right = 3
    UpLeft = 4
    UpRight = 5
    DownLeft = 6
    DownRight = 7
    Any = 8

    def opposite(self) -> 'NoteCutDirectionEnum':
        match self:
            case NoteCutDirectionEnum.Up:
                return NoteCutDirectionEnum.Down
            case NoteCutDirectionEnum.Down:
                return NoteCutDirectionEnum.Up
            case NoteCutDirectionEnum.Left:
                return NoteCutDirectionEnum.Right
            case NoteCutDirectionEnum.Right:
                return NoteCutDirectionEnum.Left
            case NoteCutDirectionEnum.UpLeft:
                return NoteCutDirectionEnum.DownRight
            case NoteCutDirectionEnum.UpRight:
                return NoteCutDirectionEnum.DownLeft
            case NoteCutDirectionEnum.DownLeft:
                return NoteCutDirectionEnum.UpRight
            case NoteCutDirectionEnum.DownRight:
                return NoteCutDirectionEnum.UpLeft
            case _:
                return NoteCutDirectionEnum.Any

    @ classmethod
    def from_movement(cls, x: Union[int, float], y: Union[int, float]) -> 'NoteCutDirectionEnum':
        '''reminder that origin is bottom left'''
        if x == 0 and y == 0:
            return cls.Any
        if x < 0 and y == 0:
            return cls.Left
        if x > 0 and y == 0:
            return cls.Right
        if x == 0 and y > 0:
            return cls.Up
        if x < 0 and y > 0:
            return cls.UpLeft
        if x > 0 and y > 0:
            return cls.UpRight
        if x == 0 and y < 0:
            return cls.Up
        if x < 0 and y < 0:
            return cls.UpLeft
        if x > 0 and y < 0:
            return cls.UpRight
        return cls.Any


class NoteCanvasPositionEnum(IntEnum):
    '''To match osu's top-left origin'''
    TopLft = 1
    TopCtr = 2
    TopRgt = 3
    MidLft = 4
    MidCtr = 5
    MidRgt = 6
    BotLft = 7
    BotCtr = 8
    BotRgt = 9


class BeatSaberHandCoordinateHolder:
    def __init__(self,
                 line: NoteLineIndexEnum,
                 layer: NoteLineLayerEnum,
                 ) -> None:
        self.index: NoteLineIndexEnum = line
        self.layer: NoteLineLayerEnum = layer

    def copy(self) -> 'BeatSaberHandCoordinateHolder':
        return type(self)(self.index, self.layer)

    def if_follow(self, cut: NoteCutDirectionEnum) -> 'BeatSaberHandCoordinateHolder':
        idx = self.index.value
        lyr = self.layer.value
        '''Remider: origin is bottom-left'''
        match cut:
            case NoteCutDirectionEnum.Up:
                lyr += 1
            case NoteCutDirectionEnum.Down:
                lyr -= 1
            case NoteCutDirectionEnum.Left:
                idx -= 1
            case NoteCutDirectionEnum.Right:
                idx += 1
            case NoteCutDirectionEnum.UpLeft:
                idx += 1
                lyr -= 1
            case NoteCutDirectionEnum.UpRight:
                idx += 1
                lyr += 1
            case NoteCutDirectionEnum.DownLeft:
                idx -= 1
                lyr -= 1
            case NoteCutDirectionEnum.DownRight:
                idx -= 1
                lyr += 1
            case _:
                pass
        return BeatSaberHandCoordinateHolder(NoteLineIndexEnum(idx), NoteLineLayerEnum(lyr))

    def follow(self, cut: NoteCutDirectionEnum):
        self.goto(self.if_follow(cut))

    def goto(self, other: 'BeatSaberHandCoordinateHolder'):
        self.index, self.layer = other.index, other.layer

    def if_goto(self, other: 'BeatSaberHandCoordinateHolder') -> NoteCutDirectionEnum:
        return NoteCutDirectionEnum.from_movement(
            other.index.value - self.index.value,
            other.layer.value - self.layer.value,
        )


class BeatSaberCoreographyHintHolder:
    def __init__(self,
                 beat_start: float,
                 beat_finish: float,
                 coordinate: BeatSaberHandCoordinateHolder,
                 coordinate_end: BeatSaberHandCoordinateHolder,
                 obstacle_type: NoteTypeEnum,
                 cut_direction: NoteCutDirectionEnum,
                 ) -> None:
        self.beat_start: float = beat_start
        self.beat_finish: float = beat_finish
        self.coordinate: BeatSaberHandCoordinateHolder = coordinate
        self.coordinate_end: BeatSaberHandCoordinateHolder = coordinate_end
        self.obstacle_type: NoteTypeEnum = obstacle_type
        self.cut_direction: NoteCutDirectionEnum = cut_direction

    def is_arc(self) -> bool:
        return self.beat_start != self.beat_finish


class BeatSaberHandPositionSimulator:
    def __init__(self,
                 hdisp: int,
                 timing: float,
                 coordinate: BeatSaberHandCoordinateHolder,
                 direction: NoteCutDirectionEnum,
                 on_arc: bool,
                 ) -> None:
        self.hdisp: int = hdisp
        self.timing: float = timing
        self.coordinate: BeatSaberHandCoordinateHolder = coordinate
        self.direction: NoteCutDirectionEnum = direction
        self.on_arc = on_arc

    def copy(self):
        return type(self)(
            self.hdisp,
            self.timing,
            self.coordinate.copy(),
            self.direction,
            self.on_arc,
        )

    def adapt(self, canvas_pos: NoteCanvasPositionEnum) -> BeatSaberHandCoordinateHolder:
        line = NoteLineIndexEnum(((canvas_pos-1) % 3)+self.hdisp)
        layer = NoteLineLayerEnum(2-((canvas_pos-1) // 3))
        return BeatSaberHandCoordinateHolder(line, layer)

    def check_cut_movement_towards(self, other: BeatSaberHandCoordinateHolder) -> NoteCutDirectionEnum:
        return self.coordinate.if_goto(other)

    def check_cut(self, beat_start: float, beat_finish: float, beat_pos: NoteCanvasPositionEnum, obstacle_type: NoteTypeEnum) -> BeatSaberCoreographyHintHolder:
        is_arc = beat_start == beat_finish
        canvas_pos = self.adapt(beat_pos)
        cut_direction = self.check_cut_movement_towards(canvas_pos)
        if (is_arc or self.on_arc) and cut_direction == NoteCutDirectionEnum.Any:
            cut_direction = self.check_cut_movement_towards(
                self.coordinate.if_follow(self.direction))
        if (is_arc or self.on_arc) and cut_direction == NoteCutDirectionEnum.Any:
            cut_direction = self.direction.opposite()
        if (is_arc or self.on_arc) and cut_direction == NoteCutDirectionEnum.Any:
            cut_direction = NoteCutDirectionEnum.Down
        return BeatSaberCoreographyHintHolder(
            beat_start, beat_finish,
            canvas_pos.copy(),
            canvas_pos.copy(),
            obstacle_type,
            cut_direction,
        )

    def cut(self, now: float, coreography: BeatSaberCoreographyHintHolder):
        self.timing = now
        self.coordinate = coreography.coordinate.copy()
        self.direction = coreography.cut_direction
        self.on_arc = coreography.is_arc()


class BeatSaberHandsPositionsSimulator:
    def __init__(self) -> None:
        self.hands = [
            BeatSaberHandPositionSimulator(
                0,
                0.0,
                BeatSaberHandCoordinateHolder(
                    NoteLineIndexEnum.LightLeft,
                    NoteLineLayerEnum.Top,
                ),
                NoteCutDirectionEnum.Down,
                True,
            ),
            BeatSaberHandPositionSimulator(
                1,
                0.0,
                BeatSaberHandCoordinateHolder(
                    NoteLineIndexEnum.LightRight,
                    NoteLineLayerEnum.Top,
                ),
                NoteCutDirectionEnum.Down,
                True,
            ),
        ]
        self.coreography_ids: List[int] = list()
        self.coreography_contents: Dict[int,
                                        BeatSaberCoreographyHintHolder] = dict()
        # -1 is at kernel's reserved space section; no pointer will be there
        self.coreography_hand_ids: List[int] = [-1, -1]
        self.last_coreography_hand_ids: List[int] = [-1, -1]

    @ property
    def left(self) -> BeatSaberHandPositionSimulator:
        return self.hands[0]

    @ left.setter
    def left(self, value):
        self.hands[0] = value

    @ property
    def right(self) -> BeatSaberHandPositionSimulator:
        return self.hands[1]

    @ right.setter
    def right(self, value):
        self.hands[1] = value

    def move_to(self,
                now: float,
                both_hands: bool,
                preferred_hands: Tuple[NoteTypeEnum, NoteTypeEnum],
                points_of_attention: List[Tuple[int, Tuple[float, float], NoteCanvasPositionEnum]]):
        for hand in range(2):  # free hand before assigning tasks
            coreography_id = self.coreography_hand_ids[hand]
            if coreography_id != -1 and self.coreography_contents[coreography_id].beat_finish < now:
                self.last_coreography_hand_ids[hand] = self.coreography_hand_ids[hand]
                self.coreography_hand_ids[hand] = -1
                if self.hands[hand].on_arc:
                    self.hands[hand].on_arc = False
                    self.hands[hand].direction = self.hands[hand].direction.opposite()
            del coreography_id
            del hand
        sorted_poas = sorted(points_of_attention,
                             key=lambda poa: (poa[1][0] != poa[1][1], -poa[1][1], poa[1][0], poa[2]))
        #                     1st: arcs first than boxes
        #                     2nd: longer arcs are more important than shorter arcs
        #                     3rd: [irrelevant now due to parent caller inner workings]
        #                     4th: last sorting criteria (kinda irrelevant, but here for sorting stability)
        for (beat_id, (beat_start, beat_finish), beat_pos) in sorted_poas:
            if now != beat_start and now != beat_finish:
                # ignore ongoing notes
                continue
            # from now on, only notes and arc beginnings
            available_hands = [NoteTypeEnum(h)
                               for h, x in enumerate(self.coreography_hand_ids)
                               if x == -1 or self.coreography_contents[x].beat_start < now]
            if len(available_hands) < 1:
                print(f'  #> WARNING: busy hands dropped beat at {now}')
                return
            active_hands = (
                [next(h for h in preferred_hands if h in available_hands)]
                if not both_hands else
                available_hands)
            del available_hands
            for active_hand_enum in active_hands:
                last_coreography: Optional[BeatSaberCoreographyHintHolder] = self.coreography_contents.get(
                    self.last_coreography_hand_ids[active_hand_enum.value])
                active_hand = self.hands[active_hand_enum.value]
                coreography = active_hand.check_cut(
                    beat_start, beat_finish, beat_pos, active_hand_enum)
                if last_coreography is not None and last_coreography.beat_finish == coreography.beat_start and last_coreography.is_arc():
                    # if the last coreography was an arc that ends where this begins
                    # update to match the beginning of this item
                    last_coreography.coordinate_end = coreography.coordinate.copy()
                del last_coreography
                active_hand.cut(now, coreography)
                self.coreography_contents[beat_id] = coreography
                self.coreography_ids.append(beat_id)
                del active_hand
                del active_hand_enum
            del beat_id
            del beat_start
            del beat_finish
            del beat_pos
        del sorted_poas

    def build_coreography(self, breaks: List[Tuple[float, float]] = list()) -> BeatSaberDifficultyV260:
        difficulty = BeatSaberDifficultyV260()
        for id_ in self.coreography_ids:
            coreography = self.coreography_contents[id_]
            difficulty.notes.append(
                BeatSaberDifficultyNote(
                    coreography.beat_start,
                    coreography.coordinate.index,
                    coreography.coordinate.layer,
                    coreography.obstacle_type,
                    coreography.cut_direction,
                )
            )
            if coreography.is_arc():
                difficulty.sliders.append(
                    BeatSaberDifficultySlider(
                        coreography.obstacle_type,
                        coreography.beat_start,
                        coreography.coordinate.index,
                        coreography.coordinate.layer,
                        1.0,
                        coreography.cut_direction,
                        coreography.beat_finish,
                        coreography.coordinate_end.index,
                        coreography.coordinate_end.layer,
                        1.0,
                        coreography.cut_direction.opposite(),
                        SliderMidAnchorModeEnum.Straight,
                    )
                )
            del coreography
            del id_
        for s, e in breaks:
            for w in (NoteLineIndexEnum.FarLeft, NoteLineIndexEnum.FarRight):
                difficulty.obstacles.append(
                    BeatSaberDifficultyObstacle(
                        s,
                        w,
                        BeatSaberDifficultyObstacleTypeEnum.FullHeightWall,
                        round((e-s)*4)/4,
                        1,
                    )
                )
        return difficulty
