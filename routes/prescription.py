import random, copy
from flask_api import status
from models.main import *
from models.appendix import *
from models.segment import *
from models.prescription import *
from flask import Blueprint, request
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)
from .utils import *
from sqlalchemy import func
from datetime import date, datetime

app_pres = Blueprint('app_pres',__name__)

@app_pres.route("/prescriptions", methods=['GET'])
@jwt_required
def getPrescriptions():
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    idSegment = request.args.get('idSegment', None)
    idDept = request.args.getlist('idDept[]')
    idDrug = request.args.getlist('idDrug[]')
    startDate = request.args.get('startDate', str(date.today()))
    endDate = request.args.get('endDate', None)
    pending = request.args.get('pending', 0)

    patients = Patient.getPatients(idSegment=idSegment, idDept=idDept, idDrug=idDrug, startDate=startDate, endDate=endDate, pending=pending)

    results = []
    for p in patients:

        patient = p[1]
        if (patient is None):
            patient = Patient()
            patient.idPatient = p[0].idPatient
            patient.admissionNumber = p[0].admissionNumber

        featuresNames = ['alerts','prescriptionScore','scoreOne','scoreTwo','scoreThree',\
                        'am','av','controlled','np','tube','diff','alertExams','interventions']
                        
        features = {'processed':True}
        if p[0].features:
            for f in featuresNames:
                features[f] = p[0].features[f] if f in p[0].features else 0
        else:
            features['processed'] = False


        results.append(dict(features, **{
            'idPrescription': p[0].id,
            'idPatient': p[0].idPatient,
            'name': patient.admissionNumber,
            'admissionNumber': patient.admissionNumber,
            'birthdate': patient.birthdate.isoformat() if patient.birthdate else '',
            'gender': patient.gender,
            'weight': patient.weight,
            'skinColor': patient.skinColor,
            'lengthStay': lenghStay(patient.admissionDate),
            'date': p[0].date.isoformat(),
            'department': str(p[2]),
            'class': 'yellow',
            'status': p[0].status,
        }))

    return {
        'status': 'success',
        'data': results
    }, status.HTTP_200_OK

class DrugList():

    def __init__(self, drugList, interventions, relations, exams):
        self.drugList = drugList
        self.interventions = interventions
        self.relations = relations
        self.exams = exams

    def getPrevIntervention(self, idDrug, idPrescription):
        result = {}
        for i in self.interventions:
            if i['idDrug'] == idDrug and i['idPrescription'] < idPrescription:
                if 'id' in result.keys() and result['id'] > i['id']: continue
                result = i;
        return result

    def getIntervention(self, idPrescriptionDrug):
        result = {}
        for i in self.interventions:
            if i['id'] == idPrescriptionDrug:
                result = i;
        return result

    def getDrugType(self, pDrugs, source, checked=False, suspended=False):
        for pd in self.drugList:

            belong = False
            if pd[0].source is None: pd[0].source = 'Medicamentos'
            if pd[0].source != source: continue
            if source == 'Soluções': belong = True
            if checked and bool(pd[0].checked) == True and bool(pd[0].suspendedDate) == False: belong = True
            if suspended and (bool(pd[0].suspendedDate) == True): belong = True
            if (not checked and not suspended) and (bool(pd[0].checked) == False and bool(pd[0].suspendedDate) == False): belong = True

            pdFrequency = 1 if pd[0].frequency in [33,44,99] else pd[0].frequency
            pdDoseconv = none2zero(pd[0].doseconv) * none2zero(pdFrequency)
            pdUnit = strNone(pd[2].id) if pd[2] else ''
            pdWhiteList = bool(pd[6].whiteList) if pd[6] is not None else False
            doseWeight = None

            alerts = []
            if self.exams and pd[6]:
                if pd[6].kidney and 'ckd' in self.exams and self.exams['ckd']['value'] and pd[6].kidney > self.exams['ckd']['value']:
                    alerts.append('Medicamento deve sofrer ajuste de posologia ou contraindicado, já que a função renal do paciente (' + str(self.exams['ckd']['value']) + ' mL/min) está abaixo de ' + str(pd[6].kidney) + ' mL/min.')

                if pd[6].liver:
                    if ('tgp' in self.exams and self.exams['tgp']['value'] and float(self.exams['tgp']['value']) > pd[6].liver) or ('tgo' in self.exams and self.exams['tgo']['value'] and float(self.exams['tgo']['value']) > pd[6].liver):
                        alerts.append('Medicamento deve sofre ajuste de posologia ou contraindicado, já que a função hepática do paciente está reduzida (acima de ' + str(pd[6].liver) + ' U/L).')

                if pd[6].elderly and self.exams['age'] > 60:
                    alerts.append('Medicamento potencialmente inapropriado para idosos, independente das comorbidades do paciente.')

                if pd[6].useWeight and none2zero(self.exams['weight']) > 0:
                    doseWeight = round(pd[0].dose / float(self.exams['weight']),2)
                    pdDoseconv = doseWeight * pdFrequency

                if pd[6].maxDose and pd[6].maxDose < pdDoseconv:
                    alerts.append('Dose diária prescrita (' + str(int(pdDoseconv)) + ') maior que a dose de alerta (' + str(pd[6].maxDose) + ') usualmente recomendada (considerada a dose diária máxima independente da indicação.')

            if pd[0].alergy == 'S':
                alerts.append('Paciente alérgico a este medicamento.')

            if pd[0].id in self.relations:
                for a in self.relations[pd[0].id]:
                    alerts.append(a)            

            if belong:
                pDrugs.append({
                    'idPrescriptionDrug': pd[0].id,
                    'idDrug': pd[0].idDrug,
                    'drug': pd[1].name if pd[1] is not None else 'Medicamento ' + str(pd[0].idDrug),
                    'np': pd[6].notdefault if pd[6] is not None else False,
                    'am': pd[6].antimicro if pd[6] is not None else False,
                    'av': pd[6].mav if pd[6] is not None else False,
                    'c': pd[6].controlled if pd[6] is not None else False,
                    'whiteList': pdWhiteList,
                    'doseWeight': str(doseWeight) + ' ' + pdUnit + '/Kg' if doseWeight else None,
                    'dose': pd[0].dose,
                    'measureUnit': { 'value': pd[2].id, 'label': pd[2].description } if pd[2] else '',
                    'frequency': { 'value': pd[3].id, 'label': pd[3].description } if pd[3] else '',
                    'dayFrequency': pd[0].frequency,
                    'doseconv': pd[0].doseconv,
                    'time': timeValue(pd[0].interval),
                    'recommendation': pd[0].notes if pd[0].notes and len(pd[0].notes.strip()) > 0 else None,
                    'period': str(pd[0].period) + 'D' if pd[0].period else '',
                    'periodDates': [],
                    'route': pd[0].route,
                    'grp_solution': pd[0].solutionGroup,
                    'stage': 'ACM' if pd[0].solutionACM == 'S' else strNone(pd[0].solutionPhase) + ' x '+ strNone(pd[0].solutionTime) + ' (' + strNone(pd[0].solutionTotalTime) + ')',
                    'infusion': strNone(pd[0].solutionDose) + ' ' + strNone(pd[0].solutionUnit),
                    'score': str(pd[5]) if not pdWhiteList else '0',
                    'source': pd[0].source,
                    'checked': bool(pd[0].checked),
                    'suspended': bool(pd[0].suspendedDate),
                    'status': pd[0].status,
                    'near': pd[0].near,
                    'prevIntervention': self.getPrevIntervention(pd[0].idDrug, pd[0].idPrescription),
                    'intervention': self.getIntervention(pd[0].id),
                    'alerts': alerts,
                    'notes': pd[7],
                    'prevNotes': pd[8]
                })
        return pDrugs

    def sortWhiteList(self, pDrugs):
        result = [p for p in pDrugs if p['whiteList'] is False]
        result.extend([p for p in pDrugs if p['whiteList']])
        return result

    def getInfusionList(self):
        result = {}
        for pd in self.drugList:
            if pd[0].solutionGroup:
                if not pd[0].solutionGroup in result:
                    result[pd[0].solutionGroup] = {'totalVol' : 0, 'amount': 0, 'vol': 0, 'speed': 0, 'unit': 'mg'}

                if pd[6] and pd[6].amount:
                    result[pd[0].solutionGroup]['vol'] = pd[0].dose
                    result[pd[0].solutionGroup]['amount'] = pd[6].amount
                    result[pd[0].solutionGroup]['unit'] = pd[6].amountUnit
                
                result[pd[0].solutionGroup]['speed'] = pd[0].solutionDose
                result[pd[0].solutionGroup]['totalVol'] += pd[0].dose

        return result


@app_pres.route('/prescriptions/<int:idPrescription>', methods=['GET'])
@jwt_required
def getPrescriptionAuth(idPrescription):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    return getPrescription(idPrescription)

def getPrescription(idPrescription):
    prescription = Prescription.getPrescription(idPrescription)

    if (prescription is None):
        return {}, status.HTTP_204_NO_CONTENT

    patient = prescription[1]
    if (patient is None):
        patient = Patient()
        patient.idPatient = prescription[0].idPatient
        patient.admissionNumber = prescription[0].admissionNumber

    lastDept = Prescription.lastDeptbyAdmission(idPrescription, patient.admissionNumber)
    drugs = PrescriptionDrug.findByPrescription(idPrescription, patient.admissionNumber)
    interventions = Intervention.findAll(admissionNumber=patient.admissionNumber)
    relations = Prescription.findRelation(idPrescription)

    exams = Exams.findLatestByAdmission(patient, prescription[0].idSegment)
    age = data2age(patient.birthdate.isoformat() if patient.birthdate else date.today().isoformat())

    examsJson = []
    alertExams = 0
    for e in exams:
        examsJson.append({'key': e, 'value': exams[e]})
        alertExams += int(exams[e]['alert'])

    exams = dict(exams, **{
        'age': age,
        'weight': patient.weight,
    })

    drugList = DrugList(drugs, interventions, relations, exams)

    pDrugs = drugList.getDrugType([], 'Medicamentos')
    pDrugs = drugList.getDrugType(pDrugs, 'Medicamentos', checked=True)
    pDrugs = drugList.getDrugType(pDrugs, 'Medicamentos', suspended=True)
    pDrugs = drugList.sortWhiteList(pDrugs)

    pSolution = drugList.getDrugType([], 'Soluções')
    pInfusion = drugList.getInfusionList()

    pProcedures = drugList.getDrugType([], 'Proced/Exames')
    pProcedures = drugList.getDrugType(pProcedures, 'Proced/Exames', checked=True)
    pProcedures = drugList.getDrugType(pProcedures, 'Proced/Exames', suspended=True)

    return {
        'status': 'success',
        'data': {
            'idPrescription': prescription[0].id,
            'idSegment': prescription[0].idSegment,
            'segmentName': prescription[5],
            'idPatient': prescription[0].idPatient,
            'name': prescription[0].admissionNumber,
            'admissionNumber': prescription[0].admissionNumber,
            'birthdate': patient.birthdate.isoformat() if patient.birthdate else '',
            'gender': patient.gender,
            'height': patient.height,
            'weight': patient.weight,
            'observation': prescription[6],
            'notes': prescription[7],
            'alert': prescription[8],
            'alertExpire': patient.alertExpire.isoformat() if patient.alertExpire else '',
            'age': age,
            'weightUser': bool(patient.user),
            'weightDate': patient.weightDate,
            'bed': prescription[0].bed,
            'record': prescription[0].record,
            'class': random.choice(['green','yellow','red']),
            'skinColor': patient.skinColor,
            'department': prescription[4],
            'lastDepartment': lastDept[0] if lastDept else 'Paciente novo',
            'patientScore': 'High',
            'date': prescription[0].date.isoformat(),
            'prescription': pDrugs,
            'solution': pSolution,
            'procedures': pProcedures,
            'infusion': [{'key': i, 'value': pInfusion[i]} for i in pInfusion],
            'interventions': [i for i in interventions if i['idPrescription'] < idPrescription],
            'alertExams': alertExams,
            'exams': examsJson[:10],
            'status': prescription[0].status,
        }
    }, status.HTTP_200_OK

@app_pres.route('/prescriptions/<int:idPrescription>', methods=['PUT'])
@jwt_required
def setPrescriptionStatus(idPrescription):
    data = request.get_json()
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    p = Prescription.query.get(idPrescription)
    if 'status' in data.keys(): p.status = data.get('status', None)
    if 'notes' in data.keys(): p.notes = data.get('notes', None)
    p.update = datetime.today()
    p.user = user.id

    return tryCommit(db, idPrescription)

@app_pres.route("/prescriptions/drug/<int:idPrescriptionDrug>/period", methods=['GET'])
@jwt_required
def getDrugPeriod(idPrescriptionDrug):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    future = request.args.get('future', None)
    results, admissionHistory = PrescriptionDrug.findByPrescriptionDrug(idPrescriptionDrug, future)

    if future and len(results[0][1]) == 0:
        if admissionHistory:
            results[0][1].append('Não há prescrição posterior para esse Medicamento')
        else:
            results[0][1].append('Não há prescrição posterior para esse Paciente')

    return {
        'status': 'success',
        'data': results[0][1]
    }, status.HTTP_200_OK

def historyExam(typeExam, examsList, segExam):
    results = []
    for e in examsList:
        if e.typeExam == typeExam:
            item = formatExam(e, e.typeExam.lower(), segExam)
            del(item['ref'])
            results.append(item)
    return results

@app_pres.route("/exams/<int:admissionNumber>", methods=['GET'])
@jwt_required
def getExamsbyAdmission(admissionNumber):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    idSegment = request.args.get('idSegment', 1)
    examsList = Exams.findByAdmission(admissionNumber)
    segExam = SegmentExam.refDict(idSegment)

    perc = {
        'h_conleuc': {
            'total' : 1,
            'relation': ['h_conlinfoc', 'h_conmono', 'h_coneos', 'h_conbaso', 'h_consegm']
        }
    }

    bufferList = {}
    typeExams = []
    for e in examsList:
        if not e.typeExam in typeExams and e.typeExam.lower() in segExam:
            key = e.typeExam.lower()
            item = formatExam(e, e.typeExam.lower(), segExam)
            item['name'] = segExam[e.typeExam.lower()].name
            item['perc'] = None
            item['history'] = historyExam(e.typeExam, examsList, segExam)
            bufferList[key] = item
            typeExams.append(e.typeExam)
            if key in perc:
                perc[key]['total'] = float(e.value)

    for p in perc:
        total = perc[p]['total']
        for r in perc[p]['relation']:
            if r in bufferList:
                val = bufferList[r]['value']
                bufferList[r]['perc'] = round((val*100)/total,1)

    results = copy.deepcopy(segExam)
    for e in segExam:
        if e in bufferList:
            results[e] = bufferList[e]
        else:
            del(results[e])

    return {
        'status': 'success',
        'data': results
    }, status.HTTP_200_OK


@app_pres.route('/patient/<int:admissionNumber>', methods=['POST'])
@jwt_required
def setPatientData(admissionNumber):
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)
    data = request.get_json()

    p = Patient.findByAdmission(admissionNumber)

    weight = data.get('weight', None)
    if weight and weight != p.weight: 
        p.weightDate = datetime.today()
        p.weight = weight
        p.user = user.id

    alertExpire = data.get('alertExpire', None)
    if alertExpire and alertExpire != p.alertExpire: 
        p.alert = data.get('alert', None)
        p.alertExpire = alertExpire
        p.alertDate = datetime.today()

    if 'height' in data.keys(): p.height = data.get('height', None)
    if 'observation' in data.keys(): p.observation = data.get('observation', None)

    p.update = datetime.today()

    if 'idPrescription' in data.keys():
        idPrescription = data.get('idPrescription')

        query = "INSERT INTO " + user.schema + ".presmed \
                    SELECT *\
                    FROM " + user.schema + ".presmed\
                    WHERE fkprescricao = " + str(int(idPrescription)) + ";"

        print(query)
        result = db.engine.execute(query) 

    return tryCommit(db, admissionNumber)

@app_pres.route('/prescriptions/drug/<int:idPrescriptionDrug>', methods=['PUT'])
@jwt_required
def setPrescriptionDrugNote(idPrescriptionDrug):
    data = request.get_json()
    user = User.find(get_jwt_identity())
    dbSession.setSchema(user.schema)

    if 'notes' in data:
        notes = data.get('notes', None)
        idDrug = data.get('idDrug', None)
        admissionNumber = data.get('admissionNumber', None)
        note = Notes.query.get((0, idPrescriptionDrug))
        newObs = False

        if note is None:
            newObs = True
            note = Notes()
            note.idPrescriptionDrug = idPrescriptionDrug
            note.idOutlier = 0

        note.idDrug = idDrug
        note.admissionNumber = admissionNumber
        note.notes = notes
        note.update = datetime.today()
        note.user  = user.id

        if newObs: db.session.add(note)

    return tryCommit(db, idPrescriptionDrug)