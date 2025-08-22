@echo off
echo Configurando acesso mobile...
echo.
echo Execute este arquivo como ADMINISTRADOR!
echo.

REM Configurar port forwarding
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=172.21.219.140
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=172.21.219.140

REM Configurar firewall
netsh advfirewall firewall add rule name="MaestroFin Frontend" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="MaestroFin Backend" dir=in action=allow protocol=TCP localport=8001

echo.
echo Configuração concluída!
echo.
echo Acesse no celular:
echo Frontend: http://192.168.1.3:3000
echo Backend: http://192.168.1.3:8001
echo.
pause
