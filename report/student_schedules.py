import os
import urllib
import jinja2
import webapp2
import logging
import datetime

import models
import authorizer

# I created a report subdirectory for various reports needed in the scheduling process.
# Since we are inside the report folder, I need to call
# os.path.dirname(os.path.dirname(...)) to go up to the parent directory.
# This is necessary because Jinja doesn't allow .. notation in extends
# in other words {% extends '../menu.html' %} is not possible.
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(os.path.dirname(__file__))),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class StudentSchedules(webapp2.RequestHandler):

  def RedirectToSelf(self, institution, session, message):
    self.redirect("/report/student_schedules?%s" % urllib.urlencode(
        {'message': message,
         'institution': institution,
         'session': session}))

  def get(self):
    auth = authorizer.Authorizer(self)
    if not (auth.CanAdministerInstitutionFromUrl() or
            auth.HasTeacherAccess()):
      auth.Redirect()
      return

    user_type = 'None'
    if auth.CanAdministerInstitutionFromUrl():
      user_type = 'Admin'
    elif auth.HasTeacherAccess():
      user_type = 'Teacher'

    institution = self.request.get("institution")
    if not institution:
      logging.fatal("no institution")
    session = self.request.get("session")
    if not session:
      logging.fatal("no session")

    message = self.request.get('message')
    session_query = urllib.urlencode({'institution': institution,
                                      'session': session})

    classes_by_id = {}
    classes = models.Classes.FetchJson(institution, session)
    for c in classes:
      classes_by_id[c['id']] = c
    students = models.Students.FetchJson(institution, session)
    last_modified_overall = datetime.datetime(2000,1,1)
    last_modified_overall_str = ''
    homerooms_by_grade = {}
    for s in students:
      if s['current_grade'] in homerooms_by_grade:
        homerooms_by_grade[s['current_grade']].add(s['current_homeroom'])
      else:
        homerooms_by_grade[s['current_grade']] = set([s['current_homeroom']])

      s['email'] = s['email'].lower()
      sched_obj = models.Schedule.FetchEntity(institution, session, s['email'])
      if not sched_obj:
        continue
      s['sched'] = sched_obj.class_ids
      s['last_modified'] = sched_obj.last_modified
      if sched_obj.last_modified:
        s['last_modified'] = str(sched_obj.last_modified.month) + '/' +\
                             str(sched_obj.last_modified.day) + '/' +\
                             str(sched_obj.last_modified.year) + ' ' +\
                             str(sched_obj.last_modified.hour).zfill(2) + ':' +\
                             str(sched_obj.last_modified.minute).zfill(2)
        if sched_obj.last_modified > last_modified_overall:
          last_modified_overall = sched_obj.last_modified
          last_modified_overall_str = s['last_modified']
      if (s['sched']):
        s['sched'] = s['sched'].split(',')
        for cId in s['sched']:
          cId_class = classes_by_id[int(cId)]
          for dp in cId_class['schedule']:
            if dp['location'] == 'Homeroom':
              s[dp['daypart']] = 'Core'
            else:
              s[dp['daypart']] = dp['location'] + ', ' + cId_class['name']
            s[dp['daypart']] = s[dp['daypart']][0:26]
    if students:
      students.sort(key=lambda(s): s['last'])
    template_values = {
      'user_email' : auth.email,
      'user_type': user_type,
      'institution' : institution,
      'session' : session,
      'message': message,
      'session_query': session_query,
      'students': students,
      'last_modified': last_modified_overall_str,
      'homerooms': sorted(homerooms_by_grade, reverse=True),
      'homerooms_by_grade': homerooms_by_grade,
    }
    template = JINJA_ENVIRONMENT.get_template('report/student_schedules.html')
    self.response.write(template.render(template_values))
