from .main import db
from sqlalchemy import func, text, and_, or_, desc, asc, distinct, cast
from routes.utils import *

class Segment(db.Model):
    __tablename__ = 'segmento'

    id = db.Column("idsegmento", db.Integer, primary_key=True)
    description = db.Column("nome", db.String, nullable=False)
    status = db.Column("status", db.Integer, nullable=False)

    def findAll():
        return db.session\
            .query(Segment)\
            .order_by(asc(Segment.description))\
            .all()

class SegmentExam(db.Model):
    __tablename__ = 'segmentoexame'

    idSegment = db.Column("idsegmento", db.Integer, primary_key=True)
    typeExam = db.Column("tpexame", db.String(100), primary_key=True)
    initials = db.Column("abrev", db.String(50), nullable=False)
    name = db.Column("nome", db.String(250), nullable=False)
    min = db.Column("min", db.Float, nullable=False)
    max = db.Column("max", db.Float, nullable=False)
    ref = db.Column("referencia", db.String(250), nullable=False)
    order = db.Column("posicao", db.Integer, nullable=False)
    active = db.Column("ativo", db.Boolean, nullable=False)
    update = db.Column("update_at", db.DateTime, nullable=False)
    user = db.Column("update_by", db.Integer, nullable=False)

    def refDict(idSegment):
        exams =  SegmentExam.query\
                    .filter(SegmentExam.idSegment == idSegment)\
                    .filter(SegmentExam.active == True)\
                    .order_by(asc(SegmentExam.order))\
                    .all()

        results = {}
        for e in exams:
            results[e.typeExam.lower()] = e

        return results

class Exams(db.Model):
    __tablename__ = 'exame'

    idExame = db.Column("fkexame", db.Integer, primary_key=True)
    idPatient = db.Column("fkpessoa", db.Integer, nullable=False)
    admissionNumber = db.Column('nratendimento', db.Integer, nullable=False)
    date = db.Column("dtexame", db.DateTime, nullable=False)
    typeExam = db.Column("tpexame", db.String, primary_key=True)
    value = db.Column("resultado", db.Float, nullable=False)
    unit = db.Column("unidade", db.String, nullable=True)

    def findByAdmission(admissionNumber):
        return db.session.query(Exams)\
                         .filter(Exams.admissionNumber == admissionNumber)\
                         .order_by(asc(Exams.typeExam),desc(Exams.date))\
                         .all()

    def findLatestByAdmission(patient, idSegment):
        examLatest = db.session.query(Exams.typeExam.label('typeExam'), func.max(Exams.date).label('date'))\
                      .select_from(Exams)\
                      .filter(Exams.admissionNumber == patient.admissionNumber)\
                      .group_by(Exams.typeExam)\
                      .subquery()

        el = db.aliased(examLatest)

        results = Exams.query\
                .join(el, and_(Exams.typeExam == el.c.typeExam, Exams.date == el.c.date))\
                .filter(Exams.admissionNumber == patient.admissionNumber)

        segExam = SegmentExam.refDict(idSegment)
        age = data2age(patient.birthdate.isoformat() if patient.birthdate else date.today().isoformat())
        
        exams = {}
        for e in segExam:
            examEmpty = { 'value': None, 'alert': False, 'ref': None, 'name': None, 'unit': None }
            examEmpty['date'] = None
            examEmpty['min'] = segExam[e].min
            examEmpty['max'] = segExam[e].max
            examEmpty['name'] = segExam[e].name
            examEmpty['initials'] = segExam[e].initials
            exams[e.lower()] = examEmpty
            if e.lower() == 'cr':
                if age > 17:
                    exams['mdrd'] = exams['cg'] = exams['ckd'] = examEmpty
                else:
                    exams['swrtz2'] = examEmpty

        for e in results:
            exams[e.typeExam.lower()] = formatExam(e, e.typeExam.lower(), segExam)
            if 'cr' in exams:
                if age > 17:
                    exams['mdrd'] = mdrd_calc(exams['cr']['value'], patient.birthdate, patient.gender, patient.skinColor)
                    exams['cg'] = cg_calc(exams['cr']['value'], patient.birthdate, patient.gender, patient.weight)
                    exams['ckd'] = ckd_calc(exams['cr']['value'], patient.birthdate, patient.gender, patient.skinColor)
                else:
                    exams['swrtz2'] = schwartz2_calc(exams['cr']['value'], patient.height)

        return exams