select * from IA_IM_MinimasReferencias
select * from TMPDocumentosCompletarFactura where DocImpoID = '444659' and tipodocumentoid = 3 
select * from IMMinima

select Ruta from IA_IM_FacturaItem as IMFI
INNER JOIN TMPDocumentosCompletarFactura as DCF ON DCF.IAItemFAC_ItemfacID = IMFI.IAItemFAC_ItemfacID
where DCF.DocImpoID = '444659' and DCF.tipodocumentoid = 3 and IMFI.IAItemFAC_ItemfacID = 396


-- Actualiza el campo IAPR_FacturaEnviadaJITClasificar a 1
UPDATE IA_IM_ProcesarFacturasIA
SET IAPR_FacturaEnviadaJITClasificar = 1
WHERE DocImpoID = '443086'

-- Actualiza el campo IAFAC_EstadosProcesamientoIA a 0
UPDATE IA_IM_Factura
SET IAFAC_EstadosProcesamientoIA = 0
WHERE IAPR_ProcesarFacturaID IN (
    SELECT IAPR_ProcesarFacturaID
    FROM IA_IM_ProcesarFacturasIA
    WHERE DocImpoID = '443086'
);

SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME COLUMN_NAME LIKE '%impo%';

select * from imdocumentoimportacion where docimpoid = 446758

select dbo.RutaDocumentosServer7(DCF.DocImpoID) + Ruta from IA_IM_FacturaItem as IMFI
INNER JOIN TMPDocumentosCompletarFactura as DCF ON DCF.IAItemFAC_ItemfacID = IMFI.IAItemFAC_ItemfacID
where DCF.DocImpoID = '444659' and DCF.tipodocumentoid = 3 and IMFI.IAItemFAC_ItemfacID = 396
 



select * from TMPDocumentosCompletarFactura

SELECT TRABAJO.IAFAC_FacturaID, TRABAJO.IAItemFAC_ItemFacID, TRABAJO.IAItemFAC_Descripcion, TRABAJO.RefProductoID
                FROM IA_IM_FacturaItem TRABAJO
                INNER JOIN BSReferenciaProducto REFPRODUCTO
                ON REFPRODUCTO.RefProductoID = TRABAJO.RefProductoID
                JOIN
                    (SELECT IAFAC_FacturaID
                    FROM IA_IM_ProcesarFacturasIA
                    RIGHT JOIN IA_IM_Factura
                    ON IA_IM_ProcesarFacturasIA.IAPR_ProcesarFacturaID = IA_IM_Factura.IAPR_ProcesarFacturaID
                    WHERE IA_IM_ProcesarFacturasIA.DocImpoID = '443086'
                    ) ENCABEZADO
                ON TRABAJO.IAFAC_FacturaID = ENCABEZADO.IAFAC_FacturaID
                WHERE REFPRODUCTO.RefProductoEstado NOT IN ('C', 'V')

SELECT 
    TRABAJO.IAFAC_FacturaID, 
    TRABAJO.IAItemFAC_ItemFacID, 
    TRABAJO.IAItemFAC_Descripcion,
    DCF.Ruta
FROM IA_IM_FacturaItem TRABAJO
INNER JOIN BSReferenciaProducto REFPRODUCTO
    ON REFPRODUCTO.RefProductoID = TRABAJO.RefProductoID
INNER JOIN TMPDocumentosCompletarFactura DCF
    ON DCF.IAItemFAC_ItemfacID = TRABAJO.IAItemFAC_ItemfacID
INNER JOIN (
    SELECT IAFAC_FacturaID
    FROM IA_IM_ProcesarFacturasIA
    LEFT JOIN IA_IM_Factura
        ON IA_IM_ProcesarFacturasIA.IAPR_ProcesarFacturaID = IA_IM_Factura.IAPR_ProcesarFacturaID
    WHERE IA_IM_ProcesarFacturasIA.DocImpoID = '443086'
) ENCABEZADO
    ON TRABAJO.IAFAC_FacturaID = ENCABEZADO.IAFAC_FacturaID
WHERE 
    REFPRODUCTO.RefProductoEstado NOT IN ('C', 'V') AND
    DCF.tipodocumentoid = 3


use DBFormularios
select * from DFAccionFormulario where AccionLink LIKE '%VUCE%'

use DBFormularios_H
select * from DFAccionFormulario where AccionLink LIKE '%VUCE%'

use [Repecev2005_H]
EXEC dbo.SP_DatosregistroInvima @DOCIMPOID = 12345, @opcion = 1;