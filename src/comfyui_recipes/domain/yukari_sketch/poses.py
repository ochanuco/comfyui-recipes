"""Every pose: its own gesture block, costume default and face departure.

A pose's face is a diff over the shared `FACE` block rather than a copied
string -- `recipe.face_block` replays the edits, and `recipe.departures`
reports what they change relative to the pose's `parent` (or `FACE` itself,
for a pose with none).
"""

from __future__ import annotations

from .models import Edit, Pose

POSES = {
    "cinema": Pose(
        action=("(walking:1.2), (holding popcorn:1.3), popcorn, (holding "
                "cup:1.25), disposable cup, (drinking straw:1.3), (full "
                "body:1.3), ")),
    "stand": Pose(
        action=("(standing:1.5), (own hands together:1.3), (hands "
                "up:1.2), (arched back:1.15), (from front:1.3), (full "
                "body:1.45), (wide shot:1.3), ")),
    "date": Pose(
        action=("(walking:1.2), (holding popcorn:1.3), popcorn, (holding "
                "cup:1.25), disposable cup, (drinking straw:1.3), (full "
                "body:1.3), (sneakers:1.3), (white sneakers:1.2), "),
        costume="outing",
        parent="cinema",
        settled_seed=737373737,
        face_edits=(
            Edit("replace", "(tareme:1.2), ",
                 "(tareme:1.2), (jitome:1.25), "),
            Edit("replace", "(half-closed eyes:1.2), ",
                 "(half-closed eyes:1.15), "),
            Edit("replace", "(unamused:1.1), ",
                 "(smirk:1.2), (smug:1.15), "),
            Edit("replace", "closed mouth, ",
                 "closed mouth, (blush:1.1), (head tilt:1.1), "),
        )),
    "cafe": Pose(
        action=("(sitting:1.3), (table:1.2), (head rest:1.35), (hand on own "
                "cheek:1.2), (elbow on table:1.15), (coffee cup:1.15), cup, "
                "saucer, (from above:1.1), (upper body:1.25), "),
        costume="outing",
        parent="date",
        canvas=(1024, 1280),
        settled_seed=7,
        face_edits=(
            Edit("replace", "(tareme:1.2), ",
                 "(tareme:1.2), (jitome:1.2), "),
            Edit("replace", "(half-closed eyes:1.2), ",
                 "(upturned eyes:1.3), (looking up:1.15), "),
            Edit("remove", "(unamused:1.1), ", ""),
            Edit("remove", "closed mouth, ", ""),
            Edit("append", "",
                 "(light smile:1.1), (parted lips:1.2), (blush:1.15), "
                 "(head tilt:1.1), "),
        )),
    "home": Pose(
        action=("(sitting:1.3), (bean bag chair:1.5), (sinking:1.2), (leaning "
                "back:1.25), (from above:1.2), (slouching:1.25), (arms at "
                "sides:1.15), (limp:1.1), (shopping bag:1.25), (paper "
                "bag:1.15), (upper body:1.25), "),
        costume="outing",
        parent="cafe",
        canvas=(1024, 1280),
        settled_seed=7,
        face_edits=(
            Edit("replace", "(tareme:1.2), ",
                 "(tareme:1.2), (jitome:1.15), "),
            Edit("replace", "(half-closed eyes:1.2), ",
                 "(half-closed eyes:1.25), "),
            Edit("replace", "(unamused:1.1), ",
                 "(head back:1.3), (looking up:1.15), "),
            Edit("replace", "closed mouth, ",
                 "(open mouth:1.25), (exhausted:1.25), (sigh:1.15), "),
            Edit("replace", "looking at viewer, ", "(blush:1.1), "),
        )),
    "bath": Pose(
        action=("(sitting:1.3), (on floor:1.3), (knee up:1.35), (outstretched "
                "leg:1.35), (leaning forward:1.2), (hands on own leg:1.4), "
                "(both hands:1.2), (holding own leg:1.2), (massage:1.3), "
                "(from above:1.1), (cowboy shot:1.25), "),
        costume="bath",
        parent="home",
        canvas=(1024, 1280),
        settled_seed=1832285246,
        face_edits=(
            Edit("replace", "(tareme:1.2), ",
                 "(tareme:1.2), (jitome:1.2), "),
            Edit("replace", "(unamused:1.1), ", "(looking down:1.25), "),
            Edit("replace", "looking at viewer, ",
                 "(blush:1.3), (flushed:1.2), "),
        )),
}
