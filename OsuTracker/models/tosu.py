from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TosuModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Folders(TosuModel):
    game: str
    skin: str
    songs: str


class Settings(TosuModel):
    showInterface: bool
    folders: Folders


class MainMenu(TosuModel):
    bassDensity: float


class Time(TosuModel):
    firstObj: int
    current: int
    full: int
    mp3: int


class Metadata(TosuModel):
    artist: str
    artistOriginal: str
    title: str
    titleOriginal: str
    mapper: str
    difficulty: str


class BPM(TosuModel):
    realtime: float
    common: float
    min: float
    max: float


class Stats(TosuModel):
    AR: float
    CS: float
    OD: float
    HP: float
    SR: float
    BPM: BPM
    circles: int
    sliders: int
    spinners: int
    holds: int
    maxCombo: int
    fullSR: float
    memoryAR: float
    memoryCS: float
    memoryOD: float
    memoryHP: float


class Path(TosuModel):
    full: str
    folder: str
    file: str
    bg: str
    audio: str


class Bm(TosuModel):
    time: Time
    id: int
    set: int
    md5: str
    rankedStatus: int
    metadata: Metadata
    stats: Stats
    path: Path


class Mods(TosuModel):
    num: int
    str: str


class Series(TosuModel):
    name: str
    data: list[float]


class StrainsAll(TosuModel):
    series: list[Series]
    xaxis: list[float]


class Pp(TosuModel):
    field_90: float = Field(alias="90")
    field_91: float = Field(alias="91")
    field_92: float = Field(alias="92")
    field_93: float = Field(alias="93")
    field_94: float = Field(alias="94")
    field_95: float = Field(alias="95")
    field_96: float = Field(alias="96")
    field_97: float = Field(alias="97")
    field_98: float = Field(alias="98")
    field_99: float = Field(alias="99")
    field_100: float = Field(alias="100")
    strains: list[float]
    strainsAll: StrainsAll


class Menu(TosuModel):
    mainMenu: MainMenu
    state: int
    gameMode: int
    isChatEnabled: int
    bm: Bm
    mods: Mods
    pp: Pp


class Combo(TosuModel):
    current: int
    max: int


class Hp(TosuModel):
    normal: float
    smooth: float


class Grade(TosuModel):
    current: str
    maxThisPlay: str


class Hits(TosuModel):
    field_0: int = Field(alias="0")
    field_50: int = Field(alias="50")
    field_100: int = Field(alias="100")
    field_300: int = Field(alias="300")
    geki: int
    katu: int
    sliderEndHits: int = Field(
        default=0,
        validation_alias=AliasChoices("sliderEndHits", "sliderEnds"),
    )
    smallTickHits: int = Field(
        default=0,
        validation_alias=AliasChoices("smallTickHits", "sliderTickHits"),
    )
    largeTickHits: int = 0
    sliderBreaks: int
    grade: Grade
    unstableRate: float
    hitErrorArray: list[int]


class GameplayPp(TosuModel):
    current: float
    fc: float
    maxThisPlay: float


class KeyState(TosuModel):
    isPressed: bool
    count: int


class KeyOverlay(TosuModel):
    k1: KeyState
    k2: KeyState
    m1: KeyState
    m2: KeyState


class PlayerScore(TosuModel):
    name: str
    score: int
    combo: int
    maxCombo: int
    mods: str
    h300: int
    geki: int
    h100: int
    katu: int
    h50: int
    h0: int
    team: int
    position: int
    isPassing: int


class Leaderboard(TosuModel):
    hasLeaderboard: bool
    isVisible: bool
    ourplayer: PlayerScore
    slots: list[PlayerScore]


class Gameplay(TosuModel):
    gameMode: int
    name: str
    score: int
    accuracy: float
    combo: Combo
    hp: Hp
    hits: Hits
    pp: GameplayPp
    keyOverlay: KeyOverlay
    leaderboard: Leaderboard
    isReplayUiHidden: bool = Field(alias="_isReplayUiHidden")


class ResultsScreen(TosuModel):
    field_0: int = Field(alias="0")
    field_50: int = Field(alias="50")
    field_100: int = Field(alias="100")
    field_300: int = Field(alias="300")
    mode: int
    name: str
    score: int
    accuracy: float
    maxCombo: int
    mods: Mods
    geki: int
    katu: int
    grade: str
    createdAt: str


class UserProfile(TosuModel):
    rawLoginStatus: int
    name: str
    accuracy: float
    rankedScore: int
    id: int
    level: float
    playCount: int
    playMode: int
    rank: int
    countryCode: int
    performancePoints: int
    rawBanchoStatus: int
    backgroundColour: str


class TeamName(TosuModel):
    left: str
    right: str


class Stars(TosuModel):
    left: int
    right: int


class Bools(TosuModel):
    scoreVisible: bool
    starsVisible: bool


class Score(TosuModel):
    left: int
    right: int


class TournamentGameplay(TosuModel):
    score: Score


class Manager(TosuModel):
    ipcState: int
    bestOF: int
    teamName: TeamName
    stars: Stars
    bools: Bools
    chat: list[Any]
    gameplay: TournamentGameplay


class Tourney(TosuModel):
    manager: Manager
    ipcClients: list[Any]


class Model(TosuModel):
    client: str
    settings: Settings
    menu: Menu
    gameplay: Gameplay
    resultsScreen: ResultsScreen
    userProfile: UserProfile
    tourney: Tourney
