--Modified drawings per designer per day
SELECT
	COUNT(1) AS 'Count',
	FORMAT(EPMD.modifyStampA2,'yyyy-MM-dd') AS 'Last Modified',
	MUSR.fullName AS 'Modified By'
FROM pdmpl90.EPMDocumentMaster AS EPMM
	INNER JOIN pdmpl90.EPMDocument AS EPMD ON EPMD.idA3masterReference = EPMM.idA2A2
	LEFT JOIN pdmpl90.WTUser AS MUSR ON MUSR.idA2A2 = EPMD.idA3B2iterationInfo

WHERE EPMM.docType = 'CADASSEMBLY' --Will only find .IAM
	AND DATEDIFF(DAY, EPMD.modifyStampA2, GETDATE()) < 365 --Only includes drawings modified during the last 365 days (For query performance)
	AND EPMD.statecheckoutInfo = 'c/i' --Keeps only checked-in assemblies
	AND EPMM.documentNumber LIKE '%-[67][0-9][0-9].%' --Will find -6## and -7## but not -6##-## and -7##-##
	AND FORMAT(EPMD.modifyStampA2,'yyyy-MM-dd') <> FORMAT(EPMM.createStampA2,'yyyy-MM-dd') --Removes references created the same day

GROUP BY
	FORMAT(EPMD.modifyStampA2,'yyyy-MM-dd'),
	MUSR.fullName

ORDER BY FORMAT(EPMD.modifyStampA2,'yyyy-MM-dd') DESC