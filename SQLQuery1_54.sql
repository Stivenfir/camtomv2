SELECT * FROM CAMTOM_Encabezado WHERE ProcesarFacturaID = '4007'

SELECT * FROM ProcesarFacturasIA where DocImpoID = 420005

SELECT * FROM ProcesarFacturasIA where DocImpoID = 418712

SELECT * FROM ProcesarFacturasIA WHERE RutaFactura like '%1-S2502-411A%'

SELECT * FROM BSReferenciaProducto WHERE RefProductoID = 959084

SELECT dbo.RutaDocumentosServer7(DocimpoID)+'\\'+SUBSTRING(RutaFactura, CHARINDEX('DS\', RutaFactura), LEN(RutaFactura)), ProcesarFacturaID 
                            FROM ProcesarFacturasIA 
                            WHERE DocImpoID = 418712 AND FacturaEnviadaProcesar = 1

SELECT TRABAJO.IDCamtom_Encabezado, TRABAJO.items_description
FROM CAMTOM_Trabajo TRABAJO
JOIN
	(SELECT IDCamtom_Encabezado
	FROM ProcesarFacturasIA
	RIGHT JOIN CAMTOM_Encabezado
	ON ProcesarFacturasIA.ProcesarFacturaID = CAMTOM_Encabezado.ProcesarFacturaID
	WHERE ProcesarFacturasIA.DocImpoID = 418712 AND ProcesarFacturasIA.FacturaEnviadaJITClasificar = 1) ENCABEZADO
	ON TRABAJO.IDCamtom_Encabezado = ENCABEZADO.IDCamtom_Encabezado

--INNER JOIN CAMTOM_Trabajo
--ON CAMTOM_Encabezado.IDCamtom_Encabezado = CAMTOM_Trabajo.IDCamtom_Encabezado

-- AND ProcesarFacturasIA.FacturaEnviadaJITClasificar = 1
