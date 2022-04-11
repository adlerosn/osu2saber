#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import math
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import PIL.Image
from generictools import (IntSpanDict, avg, distance_of_incresing_values,
                          flatten, linear_clusterization,
                          pick_the_largest_sublist)
from osutools import (OsuFileSomeMetadata, OsuHitObject, OsuModesEnum,
                      get_audio_file_from_section,
                      get_osu_hit_objects_from_section, get_osu_sections,
                      get_some_metadata_from_section)
from sabertools import (BeatSaberDifficultyV260,
                        BeatSaberHandsPositionsSimulator,
                        BeatSaberInfoButDifficulties, NoteCanvasPositionEnum,
                        NoteTypeEnum)

RGX_OSU_SCHEMA = re.compile(r'(\d+) (.+?) - (.+)')


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('osu_beatmapset_path', type=Path,
                        help='The folder inside your Songs folder that holds the audio file and .osu files')
    parser.add_argument('--songs', action='store_const',
                        default=False, const=True)
    parser.add_argument('saber_customsongs_path', type=Path, default=None, nargs='?',
                        help='The CustomSongs folder inside Beat Saber')
    return parser


def osu_folder_scheme_parser(name: str) -> Tuple[int, str, str]:
    if (match := RGX_OSU_SCHEMA.match(name)) is not None:
        a = list(match.groups())
        a[0] = int(a[0])
        return tuple(a)  # type: ignore
    else:
        raise ValueError('Regular expression did not match')


def main():
    args = get_parser().parse_args()
    path: Path = args.osu_beatmapset_path
    if not args.songs:
        bmsid, artist, title = osu_folder_scheme_parser(path.name)
        sbr = args.saber_customsongs_path or path.parent
        convert_osu2saber(
            path,
            sbr.joinpath(f'osu {bmsid} ({title} - {artist}) [saberized]'),
            bmsid, artist, title
        )
    else:
        for pth in list(path.glob('*')):
            if pth.is_dir():
                bmsid, artist, title = None, None, None
                try:
                    bmsid, artist, title = osu_folder_scheme_parser(pth.name)
                except Exception:
                    pass
                if bmsid:
                    sbr = args.saber_customsongs_path
                    o = sbr.joinpath(
                        f'osu {bmsid} ({title} - {artist}) [saberized]')
                    print(o.name)
                    convert_osu2saber(pth, o, bmsid, artist, title)


def convert_osu2saber(beatmapset_osu: Path,
                      beatmapset_saber: Path,
                      osu_beatmapset_id_default: int,
                      osu_artist_default: str,
                      osu_title_default: str):
    if not beatmapset_osu.is_dir():
        raise NotADirectoryError(beatmapset_osu)
    beatmapset_saber_number = 1
    beatmapset_saber_numbered = beatmapset_saber.with_name(
        f'{beatmapset_saber.name} #{beatmapset_saber_number}')
    if beatmapset_saber_numbered.exists() and not beatmapset_saber_numbered.is_dir():
        raise FileExistsError(beatmapset_saber_numbered)
    osu_beatmap_paths: List[Path] = list(beatmapset_osu.glob('*.osu'))
    if len(osu_beatmap_paths) <= 0:
        raise FileNotFoundError(beatmapset_osu / '*.osu')
    beatmapset_saber_numbered.mkdir(parents=True, exist_ok=True)
    # Abort on known failures
    if beatmapset_saber_numbered.joinpath('broken_audio.flag').exists():
        return True
    if beatmapset_saber_numbered.joinpath('no_eligible_osu_files.flag').exists():
        return True
    # Load osu beatmaps in this set
    osu_beatsets: List[Tuple[OsuFileSomeMetadata, List[OsuHitObject]]] = (
        read_beats_osu(beatmapset_osu, beatmapset_saber_numbered, osu_beatmap_paths,
                       osu_beatmapset_id_default, osu_artist_default, osu_title_default))
    # Abort on known failures [yes, again]
    if osu_beatsets is None:
        return True
    if len(osu_beatsets) <= 0:
        return True
    # Edge case: Beat Saber only supports 5 difficulties per beatmapset
    beatmapset_saber_number_total = math.ceil(len(osu_beatsets) / 5)
    for i in range(2, beatmapset_saber_number_total+1):
        j = beatmapset_saber.with_name(
            f'{beatmapset_saber.name} #{i}')
        j.mkdir(parents=True, exist_ok=True)
        j.joinpath('song.egg').write_bytes(
            beatmapset_saber_numbered.joinpath('song.egg').read_bytes())
        j.joinpath('cover.jpg').write_bytes(
            beatmapset_saber_numbered.joinpath('cover.jpg').read_bytes())
        del j
        del i
    # convert osu_beatsets into saber_beatsets
    saber_beatsets: Tuple[BeatSaberInfoButDifficulties,
                          List[BeatSaberDifficultyV260]] = convert_beatsets_osu2saber(osu_beatsets)
    # sort saber_beatsets by difficulty
    saber_beatsets[1].sort(key=lambda a: (
        len(a.notes),
        a.difficulty_label))
    # write converted beatmap DATs into CustomSongs
    for i in range(1, beatmapset_saber_number_total+1):
        (saber_beatsets[0]
            .with_song_sub_name(f'[{i} of {beatmapset_saber_number_total}]' if beatmapset_saber_number_total > 1 else '')
            .with_difficulties(saber_beatsets[1][i-1::beatmapset_saber_number_total])
            .write_to(beatmapset_saber.with_name(f'{beatmapset_saber.name} #{i}')))


def convert_beatsets_osu2saber(osu_beatsets: List[Tuple[OsuFileSomeMetadata, List[OsuHitObject]]]
                               ) -> Tuple[BeatSaberInfoButDifficulties, List[BeatSaberDifficultyV260]]:
    osu_metadata_merged = OsuFileSomeMetadata.merge(
        next(zip(*osu_beatsets)))  # type: ignore
    print(f'  ~> {osu_metadata_merged}')
    bsaber_attention_pointss: List[IntSpanDict[OsuHitObject]] = list()
    for osu_metadata, osu_hit_objects in osu_beatsets:
        osu_hit_objects = osu_hit_objects.copy()
        osu_hit_objects.sort(key=OsuHitObject.start_time)
        bsaber_attention_points: IntSpanDict[OsuHitObject] = IntSpanDict()
        bsaber_attention_pointss.append(bsaber_attention_points)
        for osu_hit_object in osu_hit_objects:
            for sub_hit_obj in osu_hit_object.derive_hold_subobjects():
                if sub_hit_obj.is_point():
                    bsaber_attention_points.append_point(
                        round(sub_hit_obj.start_time()*1000),
                        sub_hit_obj)
                else:
                    bsaber_attention_points.append_span(
                        (round(sub_hit_obj.start_time()*1000),
                         round(sub_hit_obj.finish_time()*1000)),
                        sub_hit_obj)
                del sub_hit_obj
            del osu_hit_object

        del osu_metadata
    saberinfo_without_difficulties = BeatSaberInfoButDifficulties(
        osu_metadata_merged.title,
        '',
        osu_metadata_merged.artist,
        osu_metadata_merged.creator,
        figure_out_bpm(bsaber_attention_pointss, 60, 410),
        customData=dict(
            generator='osu2saber',
            source='osu!',
            beatmapID=osu_metadata_merged.beatmap_id,
            beatmapSetID=osu_metadata_merged.beatmap_set_id,
            link=f'https://osu.ppy.sh/beatmaps/{osu_metadata_merged.beatmap_id}',
            link2=f'https://osu.ppy.sh/beatmapsets/{osu_metadata_merged.beatmap_set_id}',
            link3=f'https://chimu.moe/d/{osu_metadata_merged.beatmap_set_id}',
        )
    )
    round_to_beat = saberinfo_without_difficulties.round_to_beat
    conv_to_beat = saberinfo_without_difficulties.convert_to_beat
    bsaber_bpmd_attention_pointss: List[IntSpanDict[OsuHitObject]] = list()
    for bsaber_attention_points in bsaber_attention_pointss:
        bsaber_bpmd_attention_pointss.append(
            bsaber_attention_points.map_keys(round_to_beat))
        del bsaber_attention_points
    del bsaber_attention_pointss
    bsaber_difficulties: List[BeatSaberDifficultyV260] = list()
    for (osu_metadata, _), bsaber_bpmd_attention_points in zip(osu_beatsets, bsaber_bpmd_attention_pointss):
        difficulty = osu_metadata.difficulty
        multi_key: bool = osu_metadata.mode == OsuModesEnum.Mania
        del osu_metadata
        del _
        hands_pos_sim = BeatSaberHandsPositionsSimulator()
        FUTURE_LOOK = 3000
        PAST_LOOK = 3000
        bsaber_bpmd_points_of_interest = bsaber_bpmd_attention_points.points_of_interest()
        kiais: List[Tuple[int, bool]] = list()
        breaks: List[Tuple[int, int]] = list()
        combos: List[Tuple[int, int]] = list()
        LPOI = 0
        for point_of_interest in bsaber_bpmd_points_of_interest:
            active_points_of_interest = sorted(bsaber_bpmd_attention_points.active_at_point(
                point_of_interest), key=lambda a: (a.start_time(), a.new_combo(), a.is_kiai()))
            past_ones: List[OsuHitObject] = bsaber_bpmd_attention_points.active_at_span(
                (point_of_interest-PAST_LOOK,
                 point_of_interest))
            if len(past_ones) <= len(active_points_of_interest):
                breaks.append((LPOI, point_of_interest))
            del past_ones
            iw = [[min(map(OsuHitObject.coord_x, active_points_of_interest)),
                   max(map(OsuHitObject.coord_x, active_points_of_interest)),
                   ],
                  [min(map(OsuHitObject.coord_y, active_points_of_interest)),
                   max(map(OsuHitObject.coord_y, active_points_of_interest)),
                   ],
                  ]
            next_ones: List[OsuHitObject] = sorted(set(bsaber_bpmd_attention_points.active_at_span(
                (point_of_interest,
                 point_of_interest+FUTURE_LOOK))).difference(active_points_of_interest),
                key=lambda a: -a.start_time()
            )
            for next_one in next_ones:
                relevance = max(0, min(1, 1 - (
                    (round_to_beat(next_one.start_time()) - point_of_interest)/FUTURE_LOOK)))
                relevance = relevance**1.5
                cx = next_one.coord_x()
                cy = next_one.coord_y()
                del next_one
                if cx < iw[0][0]:
                    d = iw[0][0] - cx
                    iw[0][0] -= int(d*relevance)
                    del d
                if cx > iw[0][1]:
                    d = cx - iw[0][0]
                    iw[0][1] += int(d*relevance)
                    del d
                if cy < iw[1][0]:
                    d = iw[1][0] - cy
                    iw[1][0] -= int(d*relevance)
                    del d
                if cy > iw[1][1]:
                    d = cy - iw[1][0]
                    iw[1][1] += int(d*relevance)
                    del d
                del relevance
                del cx
                del cy
            del next_ones
            active_hand_goals: List[Tuple[NoteCanvasPositionEnum, OsuHitObject]] = list(
            )
            for active_point_of_interest in active_points_of_interest:
                if len(kiais) <= 0 or kiais[-1][1] != active_point_of_interest.is_kiai():
                    new_kiai = active_point_of_interest.is_kiai()
                    kiais.append((point_of_interest, new_kiai))
                    del new_kiai
                if (combo_no := active_point_of_interest.new_combo()) != 0:
                    combos.append((point_of_interest, combo_no))
                    del combo_no
                cx = active_point_of_interest.coord_x()
                pos = 0
                if iw[0][0] == iw[0][1]:
                    pos += 2
                elif cx <= iw[0][0]:
                    pos += 1
                elif cx >= iw[0][1]:
                    pos += 3
                else:
                    pos += (1 +
                            math.floor(3*((cx - iw[0][0])/(iw[0][1] - iw[0][0]))))
                del cx
                cy = active_point_of_interest.coord_y()
                if iw[1][0] == iw[1][1]:
                    pos += 3
                elif cy <= iw[1][0]:
                    pos += 0
                elif cy >= iw[1][1]:
                    pos += 6
                else:
                    pos += (3 *
                            math.floor(3*((cy - iw[1][0])/(iw[1][1] - iw[1][0]))))
                del cy
                active_hand_goals.append((NoteCanvasPositionEnum(pos),
                                          active_point_of_interest))
                del pos
                del active_point_of_interest
            del active_points_of_interest
            double_hand: bool = kiais[-1][1] and not multi_key
            preferred_hand = NoteTypeEnum(len(combos) % 2)
            least_preferred_hand = NoteTypeEnum((len(combos)+1) % 2)
            hands_pos_sim.move_to(
                conv_to_beat(point_of_interest),
                double_hand,
                (preferred_hand, least_preferred_hand),
                [
                    (id(apoi),
                     (conv_to_beat(apoi.start_time()*1000),
                        conv_to_beat(apoi.finish_time()*1000)),
                     canvas)
                    for canvas, apoi in active_hand_goals])
            del preferred_hand
            del double_hand
            del active_hand_goals
            LPOI = point_of_interest
            del point_of_interest
        del LPOI
        sidx = 1 if (len(breaks) > 0 and breaks[0][0] == 0) else 0
        breaks_adj = [(conv_to_beat(s+FUTURE_LOOK/6), conv_to_beat(e-FUTURE_LOOK/6))
                      for s, e in breaks[sidx:]]
        del sidx
        bsaber_difficulties.append(hands_pos_sim.build_coreography(breaks_adj))
        bsaber_difficulties[-1].difficulty_label = difficulty
        print('      +-> %6d %s' %
              (len(hands_pos_sim.coreography_ids), difficulty))
        del bsaber_bpmd_attention_points
        del difficulty
        del breaks_adj
        del hands_pos_sim
    del conv_to_beat
    del round_to_beat
    del bsaber_bpmd_attention_pointss
    return (saberinfo_without_difficulties, bsaber_difficulties)


def figure_out_bpm(bsaber_attention_pointss: List[IntSpanDict[OsuHitObject]], mn: float, mx: float) -> float:
    time_distance_between_notes: List[int] = sorted(
        flatten(map(distance_of_incresing_values,
                    map(IntSpanDict.points_of_interest,
                        filter(lambda a: a.retain_value(OsuHitObject.is_point),
                               bsaber_attention_pointss
                               )))))
    time_distance_between_notes = list(
        filter(lambda a: a >= 50 and a <= 600, time_distance_between_notes))
    clusters_time_distance_between_notes = linear_clusterization(
        time_distance_between_notes, 5)
    del time_distance_between_notes
    cluster_time_distance_between_notes = pick_the_largest_sublist(
        clusters_time_distance_between_notes)
    del clusters_time_distance_between_notes
    if len(cluster_time_distance_between_notes) <= 0:
        return 120.0
    avg_cluster_time_distance_between_notes = avg(
        cluster_time_distance_between_notes)
    del cluster_time_distance_between_notes
    bpm = 60000/(2*avg_cluster_time_distance_between_notes)
    if bpm <= 0:
        return 120.0
    while bpm < mn:
        bpm *= 2
    while bpm > mx:
        bpm /= 2
    return bpm


def read_beats_osu(beatmapset_osu: Path, beatmapset_saber: Path, osu_beatmap_paths: List[Path],
                   osu_beatmapset_id_default: int, osu_artist_default: str, osu_title_default: str
                   ) -> List[Tuple[OsuFileSomeMetadata, List[OsuHitObject]]]:
    osu_loaded_stuff: List[Tuple[OsuFileSomeMetadata,
                                 List[OsuHitObject]]] = list()
    for osu_beatmap_path in osu_beatmap_paths:
        osu_beatmap_text = osu_beatmap_path.read_text('utf-8', errors='ignore'
                                                      ).replace('\r\n', '\n').replace('\r', '')
        osu_beatmap_sections: Dict[str, List[str]
                                   ] = get_osu_sections(osu_beatmap_text)
        del osu_beatmap_text
        get_osu_sections
        metadata: OsuFileSomeMetadata = get_some_metadata_from_section(
            osu_beatmap_sections)
        metadata.title = metadata.title or osu_title_default
        metadata.artist = metadata.artist or osu_artist_default
        metadata.beatmap_set_id = metadata.beatmap_set_id or osu_beatmapset_id_default
        osu_hit_objects = get_osu_hit_objects_from_section(
            osu_beatmap_sections)
        if len(osu_hit_objects) and metadata.mode != OsuModesEnum.Taiko:
            print(f'  |> {metadata.mode.name} ~ {osu_beatmap_path.stem}')
            saber_beatmap_audio = beatmapset_saber.joinpath('song.egg')
            if convert_audio_osu2saber(beatmapset_osu, saber_beatmap_audio, osu_beatmap_sections):
                return list()
            saber_beatmap_thumb = beatmapset_saber.joinpath('cover.jpg')
            if convert_thumb_osu2saber(beatmapset_osu, saber_beatmap_thumb, osu_beatmap_sections):
                return list()
            osu_loaded_stuff.append((metadata, osu_hit_objects))
        del osu_beatmap_path
    if len(osu_loaded_stuff) <= 0:
        beatmapset_saber.joinpath('song.egg').unlink(missing_ok=True)
        beatmapset_saber.joinpath(
            'no_eligible_osu_files.flag').write_text(
            'no_eligible_osu_files')
    return osu_loaded_stuff


def convert_thumb_osu2saber(beatmapset_osu: Path, saber_beatmap_thumb: Path, osu_beatmap_sections: Dict[str, List[str]]) -> bool:
    if saber_beatmap_thumb.exists():
        return False
    imageline = next(filter(lambda x: x.startswith('0,0,'),
                            osu_beatmap_sections.get('Events', list())), None)
    im = PIL.Image.new('RGB', (512, 512), 0)
    if imageline is not None:
        osu_bg = beatmapset_osu.joinpath(imageline.split(',')[2].strip('"'))
        if osu_bg.exists():
            im = PIL.Image.open(str(osu_bg)).convert('RGB')
            sx, sy = im.size
            if sx != sy:
                d = min(sx, sy)
                if sx == d:
                    # L T R B
                    im = im.crop((
                        0,
                        int(sy/2 - d/2),
                        d,
                        int(sy/2 + d/2),
                    ))
                else:
                    # L T R B
                    im = im.crop((
                        int(sx/2 - d/2),
                        0,
                        int(sx/2 + d/2),
                        d,
                    ))
            im.thumbnail((512, 512))
    im.save(str(saber_beatmap_thumb))
    return False


def convert_audio_osu2saber(beatmapset_osu: Path, saber_beatmap_audio: Path, osu_beatmap_sections: Dict[str, List[str]]) -> bool:
    if not saber_beatmap_audio.exists():
        saber_beatmap_audio_tmp = saber_beatmap_audio.with_suffix('.ogg')
        osu_beatmap_audio = beatmapset_osu.joinpath(
            get_audio_file_from_section(osu_beatmap_sections))
        r = subprocess.run(
            ['ffmpeg', '-y',
                '-i', str(osu_beatmap_audio),
                '-q', '9',
                '-map_metadata', '-1',
                str(saber_beatmap_audio_tmp),
             ],
        )
        if r.returncode:
            saber_beatmap_audio.parent.joinpath(
                'broken_audio.flag').write_text(
                    'broken_audio')
            if saber_beatmap_audio_tmp.exists():
                saber_beatmap_audio_tmp.unlink()
            return True
        del r
        saber_beatmap_audio_tmp.rename(saber_beatmap_audio)
        del saber_beatmap_audio_tmp
        del osu_beatmap_audio
    del saber_beatmap_audio
    return False


if __name__ == '__main__':
    main()
