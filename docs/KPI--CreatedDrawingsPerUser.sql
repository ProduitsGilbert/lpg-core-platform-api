--Created drawings per designer per day
SELECT
	COUNT(1) AS 'Count',
	FORMAT(EPMM.createStampA2,'yyy-MM-dd') AS 'Creation Date',
	CUSR.fullName AS 'Created By'
FROM pdmpl90.EPMDocumentMaster AS EPMM
	INNER JOIN pdmpl90.EPMDocument AS EPMD ON EPMD.idA3masterReference = EPMM.idA2A2
	LEFT JOIN pdmpl90.WTUser AS CUSR ON CUSR.idA2A2 = EPMD.idA3D2iterationInfo

WHERE EPMM.docType = 'CADASSEMBLY' --Will only find .IAM
	AND DATEDIFF(DAY, EPMD.modifyStampA2, GETDATE()) < 365 --Only includes drawings modified during the last 365 days (For query performance)
	AND EPMM.documentNumber LIKE '%-[67][0-9][0-9].%' --Will find -6## and -7## but not -6##-## and -7##-##
	AND EPMM.createStampA2 = EPMD.createStampA2 --Keeps only the first iteration of the first revision

GROUP BY
	FORMAT(EPMM.createStampA2,'yyy-MM-dd'),
	CUSR.fullName

ORDER BY FORMAT(EPMM.createStampA2,'yyy-MM-dd') DESC