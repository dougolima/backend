#!/bin/bash

HOST=("localhost:5000")
printf "Authenticating..."
TOKEN=$(curl -X POST -d '{"email":"demo@noharm.ai", "password":"demo"}' -H "Content-Type: application/json" ${HOST}/authenticate | jq -r '.access_token')

SEGMENT=1
DRUG=51284
PRESCRIPTION=20381587
PRESCRIPTIONDRUG=203815876
ADMISSION=12832489

SEGMENT=1
DRUG=5
PRESCRIPTION=20
PRESCRIPTIONDRUG=20
ADMISSION=5

for LINK in reports patient-name/123 user/name-url outliers/${SEGMENT}/${DRUG} \
			intervention/reasons intervention drugs/${SEGMENT} substance \
			"prescriptions?idSegment=${SEGMENT}&date=2020-07-10" prescriptions/${PRESCRIPTION} \
			prescriptions/drug/${PRESCRIPTIONDRUG}/period \
			/static/demo/prescription/${PRESCRIPTION} \
			exams/${ADMISSION} segments segments/${SEGMENT} departments departments/free \
			segments/exams/types \
			/segments/${SEGMENT}/outliers/generate/drug/${DRUG} 
do
  COMMAND=("curl -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' '${HOST}/${LINK}'")
  printf "${LINK} "
  bash -c "${COMMAND}"
  printf "\n"
done

LINK=("drugs/${DRUG}")
DATA=('{ "idSegment": 1, "mav": true }')
COMMAND=("curl -X PUT -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"

LINK=("prescriptions/${PRESCRIPTION}")
DATA=('{ "status": "s"}')
COMMAND=("curl -X PUT -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"

LINK=("patient/${ADMISSION}")
DATA=('{ "height": 15}')
COMMAND=("curl -X POST -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"

LINK=("prescriptions/drug/${PRESCRIPTIONDRUG}")
DATA=('{ "height": 15}')
COMMAND=("curl -X PUT -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"

LINK=("prescriptions/drug/${PRESCRIPTIONDRUG}/1")
COMMAND=("curl -X PUT -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"

LINK=("intervention/${PRESCRIPTIONDRUG}")
DATA=('{ "status": "s", "admissionNumber": 12832489}')
COMMAND=("curl -X PUT -H 'Accept: application/json' -H 'Authorization: Bearer ${TOKEN}' -H 'Content-Type: application/json' ${HOST}/${LINK} -d '${DATA}'")
printf "${LINK} "
bash -c "${COMMAND}"
printf "\n"