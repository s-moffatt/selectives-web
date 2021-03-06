import webapp2
import logging
import json

import models
import authorizer
import logic

class SpotsFirm(webapp2.RequestHandler):

  def post(self):
    institution = self.request.get("institution")
    if not institution:
      logging.fatal("no institution")
    session = self.request.get("session")
    if not session:
      logging.fatal("no session")

    auth = authorizer.Authorizer(self)
    if not (auth.CanAdministerInstitutionFromUrl() or
            auth.HasTeacherAccess() or
            (auth.HasStudentAccess() and
             auth.HasPageAccess(institution, session, "schedule"))):
      self.response.status = 403 # Forbidden
      return

    class_ids = self.request.get("class_ids")
    class_ids = json.loads(class_ids)
    results = {}
    for class_id in class_ids:
      roster = models.ClassRoster.FetchEntity(institution, session, class_id)
      results[str(class_id)] = roster['remaining_firm']
    self.response.write(json.dumps(results))
