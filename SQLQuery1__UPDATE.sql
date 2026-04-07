USE [Repecev2005]
GO

UPDATE [dbo].[ProcesarFacturasIA]
   SET [Procesado] = 0
 WHERE ProcesarFacturaID = 29
GO

UPDATE [dbo].[ProcesarFacturasIA]
   SET [FacturaEnviadaProcesar] = 1
 WHERE DocImpoID = 418712
GO

UPDATE [dbo].[ProcesarFacturasIA]
   SET [FacturaEnviadaJITClasificar] = 1
 WHERE ProcesarFacturaID = 4007
GO