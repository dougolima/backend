from flask_api import status
from datetime import date, datetime, timedelta
import unicodedata

def data2age(birthdate):
    if birthdate is None: return ''

    days_in_year = 365.2425
    birthdate = birthdate.split('T')[0]
    birthdate = datetime.strptime(birthdate, '%Y-%m-%d')
    age = int ((datetime.today() - birthdate).days / days_in_year)
    return age

def data2month(birthdate):
    if birthdate is None: return ''

    month_in_year = 12
    birthdate = birthdate.split('T')[0]
    birthdate = datetime.strptime(birthdate, '%Y-%m-%d')
    age = int ((datetime.today() - birthdate).months / month_in_year)
    return age

def validate(date_text):
    try:
        return datetime.strptime(date_text, '%Y-%m-%d').date()
    except ValueError:
        return date.today()

def lenghStay(admissionDate):
    if admissionDate is None: return ''

    days = int ((datetime.today() - admissionDate).days)
    return days

def is_float(s):
    try:
        float(s)
        return True
    except:
        return False

def timeValue(time):
    numeric = str(time).strip().replace(' ','')
    if not is_float(numeric): return strNone(time).strip()
    else:
      timeList = str(time).strip().split(' ')
      if len(timeList) == 1:
        return 'Às ' + str(time).strip() + ' Horas'
      elif len(timeList) < 6:
        return 'às ' + ('h, às ').join(timeList) + 'h'
      else:
        return time

def freqValue(freq):
    if freq == 33: return 'SN'
    elif freq == 44: return 'ACM'
    elif freq == 99: return 'N/D'
    else: return freq

def none2zero(s):
    return s if is_float(s) else 0

def strNone(s):
    return '' if s is None else str(s)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii

def sortRelations(r):
  return remove_accents(r['nameB'])

def sortSubstance(s):
  return remove_accents(s['name'])

def interactionsList(drugList, splitStr):
    result = []
    for d in drugList:
        part = d.split(splitStr)
        result.append({'name': part[0], 'idDrug': part[1]})

    return result

typeRelations = {}
typeRelations['dm'] = 'Duplicidade Medicamentosa'
typeRelations['dt'] = 'Duplicidade Terapêutica'
typeRelations['it'] = 'Interação Medicamentosa'
typeRelations['iy'] = 'Incompatibilidade em Y'
typeRelations['rx'] = 'Reatividade Cruzada'

examEmpty = { 'value': None, 'alert': False, 'ref': None, 'name': None }
mdrdEmpty = dict(examEmpty, **{'initials': 'MDRD', 'name': 'Modification of Diet in Renal Disease'})
cgEmpty = dict(examEmpty, **{'initials': 'CG', 'name': 'Cockcroft-Gault'})
ckdEmpty = dict(examEmpty, **{'initials': 'CKD', 'name': 'Chronic Kidney Disease Epidemiology'})
swrtz2Empty = dict(examEmpty, **{'initials': 'Schwartz 2', 'name': 'Schwartz 2'})

class refEmpty():
    ref = initials = min = max = name = ''

def formatExam(exam, typeExam, segExam):
    if exam is not None:
        if typeExam in segExam:
            ref = segExam[typeExam]
            alert = not (exam.value >= ref.min and exam.value <= ref.max )
        else:
            ref = refEmpty()
            ref.name = typeExam
            ref.initials = typeExam
            alert = False

        return { 'value': float(exam.value), 'unit': strNone(exam.unit), 'alert': alert,\
                 'date' : exam.date.isoformat(), 'ref': ref.ref, 'initials': ref.initials,
                 'min': ref.min, 'max': ref.max, 'name': ref.name }
    else:
        examEmpty['date'] = None
        return examEmpty

def period(tuples):
    if len(tuples) > 0:
        last30 = (datetime.today() - timedelta(days=30))
        last = datetime.strptime(tuples[0].split(' ')[0]+'/'+str(last30.year), '%d/%m/%Y')
        more = last < last30

        dates = list(set([t.split(' ')[0] for t in tuples]))

        return ('+' if more else '') + str(len(dates)) + 'D'
    else:
        return '0D'

# Modification of Diet in Renal Disease
# based on https://www.kidney.org/content/mdrd-study-equation
# eGFR = 175 x (SCr)-1.154 x (age)-0.203 x 0.742 [if female] x 1.212 [if Black]
def mdrd_calc(cr, birthdate, gender, skinColor):
    if not is_float(cr): return mdrdEmpty
    if birthdate is None: return mdrdEmpty
    
    age = data2age(birthdate.isoformat())
    if age == 0: return mdrdEmpty

    eGFR = 175 * (float(cr))**(-1.154) * (age)**(-0.203)

    if gender == 'F': eGFR *= 0.742
    if skinColor == 'Negra': eGFR *= 1.212


    return { 'value': round(eGFR,1), 'ref': 'maior que 50 ml/min/1.73', 'unit': 'ml/min/1.73',
             'alert': (eGFR < 50), 'name': 'Modification of Diet in Renal Disease', 'initials': 'MDRD' }

# Cockcroft-Gault
# based on https://www.kidney.org/professionals/KDOQI/gfr_calculatorCoc
# CCr = {((140–age) x weight)/(72xSCr)} x 0.85 (if female)
def cg_calc(cr, birthdate, gender, weight):
    if not is_float(cr): return cgEmpty
    if not is_float(weight): return cgEmpty
    if birthdate is None: return cgEmpty

    age = data2age(birthdate.isoformat())
    if age == 0: return cgEmpty

    ccr = ((140 - age) * float(weight)) / (72 * float(cr))
    if gender == 'F': ccr *= 0.85

    return { 'value': round(ccr,1), 'ref': 'maior que 50 mL/min', 'unit': 'mL/min',
             'alert': (ccr < 50), 'name': 'Cockcroft-Gault', 'initials': 'CG'}

# Chronic Kidney Disease Epidemiology Collaboration
# based on https://www.kidney.org/professionals/kdoqi/gfr_calculator
def ckd_calc(cr, birthdate, gender, skinColor):
    if not is_float(cr): return ckdEmpty
    if birthdate is None: return ckdEmpty

    age = data2age(birthdate.isoformat())
    if age == 0: return ckdEmpty

    if gender == 'F':
        g = 0.7
        s = 166 if skinColor == 'Negra' else 144
        e = -1.209 if float(cr) > g else -0.329
    else:
        g = 0.9
        s = 163 if skinColor == 'Negra' else 141
        e = -1.209 if float(cr) > g else -0.411

    eGFR = s * (float(cr)/g)**(e) * (0.993)**(age)

    return { 'value': round(eGFR,1), 'ref': 'maior que 50 ml/min/1.73', 'unit': 'ml/min/1.73',
             'alert': (eGFR < 50), 'name': 'Chronic Kidney Disease Epidemiology' , 'initials': 'CKD'}

# Schwartz (2) Formula
# based on https://link.springer.com/article/10.1007%2Fs00467-014-3002-5
def schwartz2_calc(cr, height):
    if not is_float(cr): return swrtz2Empty
    if not is_float(height): return swrtz2Empty

    eGFR = (0.413 * height) / cr

    return { 'value': round(eGFR,1), 'ref': 'maior que 90 mL/min por 1.73 m²', 'unit': 'mL/min/1.73m²',
             'alert': (eGFR < 90), 'name': 'Schwartz 2' , 'initials': 'Schwartz 2'}

def tryCommit(db, recId):
    try:
        db.session.commit()
        db.session.close()
        db.session.remove()

        return {
            'status': 'success',
            'data': recId
        }, status.HTTP_200_OK
    except AssertionError as e:
        db.session.rollback()
        db.session.close()
        db.session.remove()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_400_BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        db.session.close()
        db.session.remove()

        return {
            'status': 'error',
            'message': str(e)
        }, status.HTTP_500_INTERNAL_SERVER_ERROR