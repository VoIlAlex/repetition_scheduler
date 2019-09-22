from todoist.api import TodoistAPI
import argparse
import json
import os
import datetime


name = 'repetition_scheduler'


class TodoistLecturesProject:
    def __init__(self, api_token):
        self.api = TodoistAPI(api_token)
        self.api.sync()
        self.semester_begin = None
        self.semester_end = None

        # project that will contain
        # all the tasks for lectures
        self.connected_project = None

        # days from the lecture
        # was written
        self.repetition_delays = [1, 7, 30, 60]

        # Tree-like structure
        # discipline -> lecture -> repetition
        self.disciplines = []

    def connect_to_project(self, project_name):
        projects = self.api.state['projects']
        for project in projects:
            if project['name'] == project_name:
                self.connected_project = project
                break
        else:
            print('[INFO] Cannot find a project with name {}'.format(project_name))
            print('[INFO] Creation of a new project...')
            self.connected_project = self.api.projects.add(project_name)

    def parse_schedule(self, schedule: dict):
        self.semester_begin = datetime.date.fromisoformat(
            schedule['semester']['begin']
        )
        self.semester_end = datetime.date.fromisoformat(
            schedule['semester']['end']
        )

        # parse all the disciplines
        for discipline_name in schedule:
            if discipline_name == 'semester':
                continue
            discipline = DisciplineTask(
                discipline_name
            )
            lectures_dates = []
            discipline_schedule = schedule[discipline_name]

            # parse the main schedule
            for day_of_week in discipline_schedule['main_schedule']:
                schedules_for_day = discipline_schedule['main_schedule'][day_of_week]
                for day_schedule in schedules_for_day:
                    lecture_date = datetime.date.fromisoformat(
                        day_schedule['start'])
                    lecture_period = int(day_schedule['every_n_week'])
                    # adjust lecture date to fit
                    # in day of week
                    while datetime.datetime.weekday(lecture_date) != int(day_of_week):
                        lecture_date += datetime.timedelta(days=1)

                    # collect all lectures
                    # from begin to end of
                    # the semester
                    while lecture_date < self.semester_end:
                        lectures_dates.append(lecture_date)
                        lecture_date += datetime.timedelta(
                            days=lecture_period * 7)

            # parse the extra schedule
            for day_of_week in discipline_schedule['extra_schedule']:
                schedules_for_day = discipline_schedule['extra_schedule'][day_of_week]
                for day_schedule in schedules_for_day:
                    lecture_date = datetime.date.fromisoformat(
                        day_schedule['date']
                    )
                    lectures_dates.append(lecture_date)

            # sort lectures by dates
            lectures_dates.sort()

            for i, lecture_date in enumerate(lectures_dates):
                lecture_name = discipline_name + ". " + "Lecture " + str(i+1) + \
                    ' ({})'.format(lecture_date)
                lecture = LectureTask(
                    name=lecture_name,
                    date=lecture_date
                )

                # generate repetitions
                # for a given lecture
                for j, delay in enumerate(self.repetition_delays):
                    repetition_name = discipline_name + ". " + "Lecture " + str(i + 1) + \
                        '. ' + "Repetition " + str(j+1)
                    repetition_due_date = lecture_date + \
                        datetime.timedelta(days=delay)

                    # if a repetiton
                    # goes out of semester
                    flag_overflow = False
                    if repetition_due_date >= self.semester_end:
                        repetition = self.semester_end
                        flag_overflow = True

                    # add repetition to a lecture
                    repetition = RepetitionTask(
                        repetition_name,
                        repetition_due_date
                    )
                    lecture.add_repetition(repetition)

                    if flag_overflow:
                        break

                # add a completed lecture
                # to a current
                # discipline
                discipline.add_lecture(lecture)

            # save a completed
            # discipline
            self.disciplines.append(discipline)

        projects = self.api.state['projects']
        for project in projects:
            if project['name'] == 'Lectures':
                university_project = project
                break
        # if project wasn't found
        # create one
        else:
            university_project = self.api.projects.add('Lectures')
            self.api.commit()
        return university_project

    def upload(self):
        for discipline in self.disciplines:
            print('[INFO] Commiting the discipline \'{}\'...'.format(
                discipline.name))

            discipline_project = self.api.projects.add(
                discipline.name,
                parent_id=self.connected_project['id']
            )
            for lecture in discipline.lectures:
                print('[INFO] Commiting the lecture \'{}\'...'.format(
                    lecture.name))
                lecture_task = self.api.items.add(
                    lecture.name,
                    project_id=discipline_project['id']
                )
                for repetition in lecture.repetitions:
                    print('[INFO] Commiting the repetition \'{}\'...'.format(
                        repetition.name))
                    repetition_task = self.api.items.add(
                        repetition.name,
                        date_string=str(repetition.due_date),
                        project_id=discipline_project['id'],
                        parent_id=lecture_task['id']
                    )
                self.api.commit()
            self.api.commit()

    def clear_project(self):
        project_tasks = [task for task in self.api.state['items']
                         if task['project_id'] == self.connected_project['id']]
        for i, task in enumerate(project_tasks):
            if i % 25 == 0:
                self.api.commit()
            task.delete()


class Task:
    def __init__(self, name, due_date):
        self.name = name
        self.due_date = due_date


class DisciplineTask(Task):
    def __init__(self, name):
        Task.__init__(self, name, due_date=None)
        self.lectures = []

    def add_lecture(self, lecture):
        self.lectures.append(lecture)
        lecture.parent_discipline = self


class LectureTask(Task):
    def __init__(self, name, date):
        Task.__init__(self, name, due_date=None)
        self.date = date
        self.parent_discipline = None
        self.repetitions = []

    def add_repetition(self, repetition):
        self.repetitions.append(repetition)
        repetition.parent_lecture = self


class RepetitionTask(Task):
    def __init__(self, name, due_date):
        Task.__init__(self, name, due_date)
        self.parent_lecture = None


def parse_args():
    TODOIST_API_KEY = '9af713fb7787aa936d691eba3ae1dcbf5bbd11cc'
    DEFAULT_SCHEDULES_PATH = 'schedules.json'
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--token',
        help='Todoist API token',
        default=TODOIST_API_KEY
    )
    parser.add_argument(
        '-s', '--schedules',
        help='path to file with schedules',
        default=DEFAULT_SCHEDULES_PATH
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    schedule = json.load(
        open(
            os.path.join(os.path.dirname(__file__), args.schedules),
            'r',
            encoding='utf-8'
        )
    )
    labs_project = TodoistLecturesProject(args.token)
    labs_project.connect_to_project('Lectures')
    labs_project.parse_schedule(schedule)
    labs_project.clear_project()
    labs_project.upload()
