#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from collections import defaultdict
from typing import (Callable, Collection, DefaultDict, Dict, Generator,
                    Generic, Iterable, List, Tuple, TypeVar, Union)

GT = TypeVar('GT')


def identity(v: GT) -> GT: return v


def _flatten(iie: Iterable[Iterable[GT]]) -> Generator[GT, None, None]:
    return (e for ie in iie for e in ie)


def flatten(ii: Iterable[Iterable[GT]]) -> List[GT]:
    return list(_flatten(ii))


def pick_most_frequent_or_default_sorting(coll: List[GT]) -> GT:
    return sorted(freq_rank(coll).items(), key=lambda a: (-a[1], a[0]))[0][0]


def freq_rank(coll: Iterable[GT]) -> Dict[GT, int]:
    dd: DefaultDict[GT, int] = defaultdict(int)
    for itm in coll:
        dd[itm] += 1
    return dict(dd)


class IntSpanDict(Generic[GT]):
    def __init__(self,
                 events: Dict[int, List[GT]] = None,
                 spans: List[Tuple[Tuple[int, int], GT]] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events: Dict[int, List[GT]
                          ] = events if events is not None else dict()
        self.spans: List[Tuple[Tuple[int, int], GT]
                         ] = spans if spans is not None else list()

    def _filter_span_from_point_generator(self, point: int) -> Generator[GT, None, None]:
        yield from []
        for span, value in self.spans:
            if span[0] <= point and point <= span[1]:
                yield value

    def _filter_event_from_span_generator(self, span: Tuple[int, int]) -> Generator[GT, None, None]:
        yield from []
        for point, values in self.events.items():
            if span[0] <= point and point <= span[1]:
                yield from values

    def _filter_span_from_span_generator(self, span_request: Tuple[int, int]) -> Generator[GT, None, None]:
        yield from []
        for span_knowledge, value in self.spans:
            if (
                ((span_request[0] >= span_knowledge[0]) and (span_request[0] <= span_knowledge[1])) or
                ((span_request[1] >= span_knowledge[0]) and (span_request[1] <= span_knowledge[1])) or
                ((span_knowledge[0] >= span_request[0]) and (span_knowledge[0] <= span_request[1])) or
                ((span_knowledge[1] >= span_request[0]) and (span_knowledge[1] <= span_request[1])) or
                (False)
            ):
                yield value

    def append_point(self, point: int, value: GT):
        if point not in self.events:
            self.events[point] = list()
        self.events[point].append(value)

    def append_span(self, span: Tuple[int, int], value: GT):
        self.spans.append((span, value))

    def active_at_point(self, point: int) -> List[GT]:
        return (self.events.get(point, list()) +
                list(self._filter_span_from_point_generator(point)))

    def active_at_span(self, span: Tuple[int, int]) -> List[GT]:
        return (list(self._filter_event_from_span_generator(span)) +
                list(self._filter_span_from_span_generator(span)))

    def points_of_interest(self) -> List[int]:
        return sorted(
            set(self.events.keys()) |
            set(_flatten(next(zip(*self.spans), list())))
        )

    def map_keys(self, mapper: Callable[[int], int]) -> 'IntSpanDict[GT]':
        other = type(self)()
        for (ks, ke), v in self.spans:
            nks = mapper(ks)
            nke = mapper(ke)
            if nks == nke:
                other.append_point(nks, v)
            else:
                other.append_span((nks, nke), v)
        for k, vs in self.events.items():
            for v in vs:
                other.append_point(mapper(k), v)
        return other

    def retain_value(self, condition: Callable[[GT], bool]) -> 'IntSpanDict[GT]':
        other = type(self)()
        for k1, v in self.spans:
            if condition(v):
                other.append_span(k1, v)
        for k2, vs in self.events.items():
            for v in vs:
                if condition(v):
                    other.append_point(k2, v)
        return other

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.events!r})'


def _distance_of_incresing_values(values: List[int]) -> Generator[int, None, None]:
    yield from []
    for i in range(1, len(values)):
        yield values[i]-values[i-1]


def distance_of_incresing_values(values: List[int]) -> List[int]:
    return list(_distance_of_incresing_values(values))


def linear_clusterization(points: List[GT], eps=1) -> List[List[GT]]:
    if len(points) == 0:
        return list()
    points_sorted = sorted(points)  # type: ignore
    clusters = [[points_sorted[0]]]
    for point in points_sorted[1:]:
        if point > clusters[-1][-1] + eps:
            clusters.append([])
        clusters[-1].append(point)
    return clusters


def pick_the_largest_sublist(lle: List[List[GT]]) -> List[GT]:
    if len(lle) == 0:
        return list()
    s = max(map(len, lle))
    return next(filter(lambda a: len(a) == s, lle))


def avg(e: Collection[Union[float, int]]) -> float:
    return sum(e)/len(e)
