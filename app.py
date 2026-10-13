from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

# Use an environment variable for the secret key in production.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "faculty-timetable-demo-key"
)

# Keep the database in the same directory as app.py.
DB = Path(__file__).with_name("faculty_timetable.db")


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT,
            max_hours INTEGER NOT NULL DEFAULT 16
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_no TEXT NOT NULL UNIQUE,
            building TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 40,
            room_type TEXT NOT NULL DEFAULT 'Classroom'
        );

        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            UNIQUE(day, start_time, end_time)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            weekly_hours INTEGER NOT NULL DEFAULT 3,
            FOREIGN KEY(faculty_id) REFERENCES faculty(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            FOREIGN KEY(assignment_id)
                REFERENCES assignments(id) ON DELETE CASCADE,
            FOREIGN KEY(room_id) REFERENCES rooms(id),
            FOREIGN KEY(slot_id) REFERENCES slots(id),
            UNIQUE(room_id, slot_id)
        );

        CREATE TABLE IF NOT EXISTS substitutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timetable_id INTEGER NOT NULL,
            substitute_faculty_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Approved',
            FOREIGN KEY(timetable_id)
                REFERENCES timetable(id) ON DELETE CASCADE,
            FOREIGN KEY(substitute_faculty_id) REFERENCES faculty(id)
        );
        """)

        # Add sample data only when the relevant tables are empty.
        if con.execute("SELECT COUNT(*) FROM faculty").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO faculty(name, department, email, max_hours)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        "Dr. Ananya Rao",
                        "Computer Science",
                        "ananya.rao@woxsen.edu.in",
                        16
                    ),
                    (
                        "Prof. Rohan Mehta",
                        "Computer Science",
                        "rohan.mehta@woxsen.edu.in",
                        14
                    ),
                    (
                        "Dr. Priya Sharma",
                        "Electronics",
                        "priya.sharma@woxsen.edu.in",
                        16
                    ),
                    (
                        "Prof. Arjun Nair",
                        "Mathematics",
                        "arjun.nair@woxsen.edu.in",
                        12
                    )
                ]
            )

        if con.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO courses(code, title, department, credits)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        "CSE201",
                        "Database Management Systems",
                        "Computer Science",
                        4
                    ),
                    (
                        "CSE203",
                        "Data Structures",
                        "Computer Science",
                        4
                    ),
                    (
                        "ECE202",
                        "Digital Systems",
                        "Electronics",
                        3
                    ),
                    (
                        "MAT201",
                        "Engineering Mathematics",
                        "Mathematics",
                        4
                    )
                ]
            )

        if con.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO rooms(room_no, building, capacity, room_type)
                VALUES (?, ?, ?, ?)
                """,
                [
                    ("A-204", "Academic Block A", 60, "Classroom"),
                    ("A-305", "Academic Block A", 45, "Classroom"),
                    ("LAB-02", "Innovation Block", 35, "Computer Lab"),
                    ("B-110", "Academic Block B", 50, "Classroom")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO slots(day, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                [
                    ("Monday", "09:00", "10:00"),
                    ("Monday", "10:00", "11:00"),
                    ("Monday", "11:15", "12:15"),
                    ("Tuesday", "09:00", "10:00"),
                    ("Tuesday", "10:00", "11:00"),
                    ("Wednesday", "11:15", "12:15"),
                    ("Thursday", "13:00", "14:00"),
                    ("Friday", "14:00", "15:00")
                ]
            )

        if con.execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO assignments(
                    faculty_id, course_id, section, weekly_hours
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (1, 1, "CSE-A", 4),
                    (2, 2, "CSE-A", 4),
                    (3, 3, "ECE-A", 3),
                    (4, 4, "CSE-B", 4)
                ]
            )

        if con.execute("SELECT COUNT(*) FROM timetable").fetchone()[0] == 0:
            con.executemany(
                """
                INSERT INTO timetable(assignment_id, room_id, slot_id)
                VALUES (?, ?, ?)
                """,
                [
                    (1, 1, 1),
                    (2, 3, 2),
                    (3, 2, 4),
                    (4, 4, 6)
                ]
            )

        if con.execute("SELECT COUNT(*) FROM substitutions").fetchone()[0] == 0:
            con.execute(
                """
                INSERT INTO substitutions(
                    timetable_id, substitute_faculty_id, reason, status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    1,
                    2,
                    "Faculty attending a conference",
                    "Approved"
                )
            )


# Initialize the database when the application starts.
init_db()


@app.route("/")
def dashboard():
    with connect() as con:
        stats = {
            "faculty": con.execute(
                "SELECT COUNT(*) FROM faculty"
            ).fetchone()[0],
            "courses": con.execute(
                "SELECT COUNT(*) FROM courses"
            ).fetchone()[0],
            "rooms": con.execute(
                "SELECT COUNT(*) FROM rooms"
            ).fetchone()[0],
            "classes": con.execute(
                "SELECT COUNT(*) FROM timetable"
            ).fetchone()[0]
        }

        schedule = con.execute("""
            SELECT
                t.id,
                s.day,
                s.start_time,
                s.end_time,
                c.code,
                c.title,
                a.section,
                f.name AS faculty,
                r.room_no
            FROM timetable t
            JOIN slots s ON s.id = t.slot_id
            JOIN assignments a ON a.id = t.assignment_id
            JOIN faculty f ON f.id = a.faculty_id
            JOIN courses c ON c.id = a.course_id
            JOIN rooms r ON r.id = t.room_id
            ORDER BY
                CASE s.day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    ELSE 5
                END,
                s.start_time
            LIMIT 7
        """).fetchall()

        workload = con.execute("""
            SELECT
                f.name,
                f.department,
                f.max_hours,
                COALESCE(SUM(a.weekly_hours), 0) AS assigned
            FROM faculty f
            LEFT JOIN assignments a ON a.faculty_id = f.id
            GROUP BY f.id
            ORDER BY assigned DESC
        """).fetchall()

    return render_template(
        "dashboard.html",
        stats=stats,
        schedule=schedule,
        workload=workload
    )


@app.route("/faculty", methods=["GET", "POST"])
def faculty():
    with connect() as con:
        if request.method == "POST":
            try:
                con.execute(
                    """
                    INSERT INTO faculty(name, department, email, max_hours)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.form["name"].strip(),
                        request.form["department"].strip(),
                        request.form.get("email", "").strip(),
                        int(request.form["max_hours"])
                    )
                )
                flash("Faculty member added successfully.", "success")

            except Exception:
                flash(
                    "Could not add faculty. Check the details and try again.",
                    "error"
                )

            return redirect(url_for("faculty"))

        rows = con.execute("""
            SELECT
                f.*,
                COALESCE(SUM(a.weekly_hours), 0) AS assigned
            FROM faculty f
            LEFT JOIN assignments a ON a.faculty_id = f.id
            GROUP BY f.id
            ORDER BY f.name
        """).fetchall()

    return render_template("faculty.html", rows=rows)


@app.route("/courses", methods=["GET", "POST"])
def courses():
    with connect() as con:
        if request.method == "POST":
            try:
                con.execute(
                    """
                    INSERT INTO courses(code, title, department, credits)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.form["code"].strip().upper(),
                        request.form["title"].strip(),
                        request.form["department"].strip(),
                        int(request.form["credits"])
                    )
                )
                flash("Course added successfully.", "success")

            except Exception:
                flash(
                    "Could not add course. Course code may already exist.",
                    "error"
                )

            return redirect(url_for("courses"))

        rows = con.execute(
            "SELECT * FROM courses ORDER BY code"
        ).fetchall()

    return render_template("courses.html", rows=rows)


@app.route("/rooms", methods=["GET", "POST"])
def rooms():
    with connect() as con:
        if request.method == "POST":
            try:
                con.execute(
                    """
                    INSERT INTO rooms(room_no, building, capacity, room_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.form["room_no"].strip().upper(),
                        request.form["building"].strip(),
                        int(request.form["capacity"]),
                        request.form["room_type"]
                    )
                )
                flash("Room added successfully.", "success")

            except Exception:
                flash(
                    "Could not add room. Room number may already exist.",
                    "error"
                )

            return redirect(url_for("rooms"))

        rows = con.execute(
            "SELECT * FROM rooms ORDER BY room_no"
        ).fetchall()

    return render_template("rooms.html", rows=rows)


@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    with connect() as con:
        if request.method == "POST":
            faculty_id = int(request.form["faculty_id"])
            course_id = int(request.form["course_id"])
            section = request.form["section"].strip().upper()
            weekly_hours = int(request.form["weekly_hours"])

            exists = con.execute(
                """
                SELECT 1 FROM assignments
                WHERE faculty_id = ? AND course_id = ? AND section = ?
                """,
                (faculty_id, course_id, section)
            ).fetchone()

            if exists:
                flash(
                    "This faculty/course/section assignment already exists.",
                    "error"
                )
            else:
                faculty_row = con.execute(
                    "SELECT name, max_hours FROM faculty WHERE id = ?",
                    (faculty_id,)
                ).fetchone()

                if faculty_row is None:
                    flash("Selected faculty member was not found.", "error")
                else:
                    current = con.execute(
                        """
                        SELECT COALESCE(SUM(weekly_hours), 0)
                        FROM assignments
                        WHERE faculty_id = ?
                        """,
                        (faculty_id,)
                    ).fetchone()[0]

                    if current + weekly_hours > faculty_row["max_hours"]:
                        flash(
                            f"Weekly workload limit exceeded. "
                            f"{faculty_row['name']} has {current} assigned "
                            f"hours and a limit of {faculty_row['max_hours']}.",
                            "error"
                        )
                    else:
                        con.execute(
                            """
                            INSERT INTO assignments(
                                faculty_id, course_id, section, weekly_hours
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                faculty_id,
                                course_id,
                                section,
                                weekly_hours
                            )
                        )
                        flash(
                            "Faculty-course assignment added. "
                            "It is now available in the timetable planner.",
                            "success"
                        )

            return redirect(url_for("assignments"))

        staff = con.execute(
            "SELECT * FROM faculty ORDER BY name"
        ).fetchall()

        courses_list = con.execute(
            "SELECT * FROM courses ORDER BY code"
        ).fetchall()

        rows = con.execute("""
            SELECT
                a.id,
                f.name AS faculty,
                f.department,
                c.code,
                c.title,
                c.department AS course_department,
                a.section,
                a.weekly_hours
            FROM assignments a
            JOIN faculty f ON f.id = a.faculty_id
            JOIN courses c ON c.id = a.course_id
            ORDER BY c.code, a.section, f.name
        """).fetchall()

    return render_template(
        "assignments.html",
        staff=staff,
        courses=courses_list,
        rows=rows
    )


@app.route("/timetable", methods=["GET", "POST"])
def timetable():
    with connect() as con:
        if request.method == "POST":
            assignment_id = int(request.form["assignment_id"])
            room_id = int(request.form["room_id"])
            slot_id = int(request.form["slot_id"])

            clash = con.execute("""
                SELECT t.id
                FROM timetable t
                JOIN assignments a ON a.id = t.assignment_id
                WHERE t.slot_id = ?
                  AND (
                      t.room_id = ?
                      OR a.faculty_id = (
                          SELECT faculty_id
                          FROM assignments
                          WHERE id = ?
                      )
                  )
            """, (slot_id, room_id, assignment_id)).fetchone()

            if clash:
                flash(
                    "Conflict detected: that room or faculty member "
                    "is already scheduled in this time slot.",
                    "error"
                )
            else:
                con.execute(
                    """
                    INSERT INTO timetable(assignment_id, room_id, slot_id)
                    VALUES (?, ?, ?)
                    """,
                    (assignment_id, room_id, slot_id)
                )
                flash(
                    "Timetable entry created. "
                    "No room/faculty conflict found.",
                    "success"
                )

            return redirect(url_for("timetable"))

        rows = con.execute("""
            SELECT
                t.id,
                s.day,
                s.start_time,
                s.end_time,
                c.code,
                c.title,
                a.section,
                f.name AS faculty,
                r.room_no
            FROM timetable t
            JOIN slots s ON s.id = t.slot_id
            JOIN assignments a ON a.id = t.assignment_id
            JOIN faculty f ON f.id = a.faculty_id
            JOIN courses c ON c.id = a.course_id
            JOIN rooms r ON r.id = t.room_id
            ORDER BY
                CASE s.day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    ELSE 5
                END,
                s.start_time
        """).fetchall()

        assignments_list = con.execute("""
            SELECT
                a.id,
                c.code,
                c.title,
                a.section,
                f.name AS faculty
            FROM assignments a
            JOIN courses c ON c.id = a.course_id
            JOIN faculty f ON f.id = a.faculty_id
            ORDER BY c.code, a.section, f.name
        """).fetchall()

        rooms_list = con.execute(
            "SELECT * FROM rooms ORDER BY room_no"
        ).fetchall()

        slots = con.execute("""
            SELECT *
            FROM slots
            ORDER BY
                CASE day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    ELSE 5
                END,
                start_time
        """).fetchall()

    return render_template(
        "timetable.html",
        rows=rows,
        assignments=assignments_list,
        rooms=rooms_list,
        slots=slots
    )


@app.route("/substitutions", methods=["GET", "POST"])
def substitutions():
    with connect() as con:
        if request.method == "POST":
            con.execute(
                """
                INSERT INTO substitutions(
                    timetable_id, substitute_faculty_id, reason, status
                )
                VALUES (?, ?, ?, 'Approved')
                """,
                (
                    int(request.form["timetable_id"]),
                    int(request.form["substitute_faculty_id"]),
                    request.form["reason"].strip()
                )
            )

            flash("Substitution recorded.", "success")
            return redirect(url_for("substitutions"))

        rows = con.execute("""
            SELECT
                sub.id,
                sub.reason,
                sub.status,
                s.day,
                s.start_time,
                c.code,
                a.section,
                f.name AS original_faculty,
                sf.name AS substitute_faculty,
                r.room_no
            FROM substitutions sub
            JOIN timetable t ON t.id = sub.timetable_id
            JOIN slots s ON s.id = t.slot_id
            JOIN assignments a ON a.id = t.assignment_id
            JOIN courses c ON c.id = a.course_id
            JOIN faculty f ON f.id = a.faculty_id
            JOIN faculty sf ON sf.id = sub.substitute_faculty_id
            JOIN rooms r ON r.id = t.room_id
            ORDER BY sub.id DESC
        """).fetchall()

        classes = con.execute("""
            SELECT
                t.id,
                s.day,
                s.start_time,
                c.code,
                a.section,
                f.name AS faculty
            FROM timetable t
            JOIN slots s ON s.id = t.slot_id
            JOIN assignments a ON a.id = t.assignment_id
            JOIN courses c ON c.id = a.course_id
            JOIN faculty f ON f.id = a.faculty_id
            ORDER BY t.id
        """).fetchall()

        staff = con.execute(
            "SELECT * FROM faculty ORDER BY name"
        ).fetchall()

    return render_template(
        "substitutions.html",
        rows=rows,
        classes=classes,
        staff=staff
    )


@app.route("/delete-class/<int:item_id>", methods=["POST"])
def delete_class(item_id):
    with connect() as con:
        con.execute(
            "DELETE FROM timetable WHERE id = ?",
            (item_id,)
        )

    flash("Timetable entry removed.", "success")
    return redirect(url_for("timetable"))


if __name__ == "__main__":
    app.run(debug=True)