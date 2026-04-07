SELECT * FROM IMFactura WHERE FacturaNumero = '9103203497'
 
SELECT * FROM IMItemFactura WHERE FacturaID=1032066

SELECT * FROM BSReferenciaProducto WHERE PosArancelariaID = '7318240000'

SELECt * FROM BSReferenciaProducto WHERE RefClienteID = 9360 and RefProductoDescripcion LIKE ''

SELECt * FROM BSReferenciaProducto WHERE RefProductoDescripcion IS null
                  AND PosArancelariaID IS null
                  AND RefProductoMarca = 'SIN MARCA'
                  AND RefClienteID = 1150

SELECT * FROM ProcesarFacturasIA WHERE docimpoid = 420005
SELECT * FROM ProcesarFacturasIA WHERE ProcesarFacturaID = 870

/* si el cliente está en la siguiente tabla se coloca la referencia en el campo refcointernocliente 
	si no está ahi, se coloca en refproductoreferencia 42611*/
SELECT * FROM BSClienteTipoFactura WHERE CLIENTEID = 30759

SELECT * FROM vExportadorCliente WHERE PJRazonSocial LIKE '%PRICESMART%'

SELECT * FROM vProveedor WHERE NombreCompleto LIKE '%SINO CROWN INTERNATIONAL PTE. LTD%'

SELECT RutaFactura FROM ProcesarFacturasIA WHERE DocImpoID =419830

DELETE FROM CAMTOM_Trabajo
WHERE IDCamtom_Encabezado = 1;

DELETE FROM CAMTOM_Encabezado
WHERE IDCamtom_Encabezado = 3;

SELECT * FROM CAMTOM_Trabajo

DELETE FROM ProcesarFacturasIA WHERE ProcesarFacturaID = 870

SELECT * FROM CAMTOM_Encabezado

SELECT * , dbo.RutaDocumentosServer7(DocimpoID)+RutaFactura 
FROM ProcesarFacturasIA 
WHERE DocImpoID = 420963 AND FacturaEnviadaProcesar = 1