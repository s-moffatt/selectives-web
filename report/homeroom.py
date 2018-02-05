import os
import urllib
import jinja2
import webapp2

import models
import authorizer

# Since we are inside the report directory, but Jinja doesn't allow
# {% extends '../menu.html' %}, call os.path.dirname(os.path.dirname())
# to go up to the parent directory.
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(os.path.dirname(__file__))),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

dayOrder = ['Mon A', 'Mon B', 'Tues A', 'Tues B',
            'Thurs A', 'Thurs B', 'Fri A', 'Fri B']

def listOrder(c):
  if 'instructor' in c:
    return (c['name'],
            dayOrder.index(c['schedule'][0]['daypart']),
            c['instructor'])
  else:
    return (c['name'],
            dayOrder.index(c['schedule'][0]['daypart']))

class Homeroom(webapp2.RequestHandler):

  def RedirectToSelf(self, institution, session, message):
    self.redirect("/report/homeroom?%s" % urllib.urlencode(
        {'message': message,
         'institution': institution,
         'session': session}))

  def get(self):
    auth = authorizer.Authorizer(self)
    if not auth.CanAdministerInstitutionFromUrl():
      auth.Redirect()
      return

    institution = self.request.get("institution")
    if not institution:
      logging.fatal("no institution")
    session = self.request.get("session")
    if not session:
      logging.fatal("no session")

    message = self.request.get('message')
    session_query = urllib.urlencode({'institution': institution,
                                      'session': session})

    classes = models.Classes.FetchJson(institution, session)
    if classes:
      classes.sort(key=listOrder)
    students = models.Students.FetchJson(institution, session)
    for s in students:
      s['email'] = s['email'].lower()
    if students:
      students.sort(key=lambda(s): s['last'])
    template_values = {
      'user_email' : auth.email,
      'institution' : institution,
      'session' : session,
      'message': message,
      'session_query': session_query,
      'classes': classes,
      'students': students,
    }
    template = JINJA_ENVIRONMENT.get_template('report/homeroom.html')
    self.response.write(template.render(template_values))