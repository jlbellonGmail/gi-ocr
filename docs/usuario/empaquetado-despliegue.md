# Empaquetado y Despliegue

## Para qué sirve

Permite llevar gi-ocr (captura y extracción OCR de comprobantes) a probar
en un servidor o equipo propio — el tuyo o el de un cliente — con un solo
comando, sin instalar Python, crear un entorno virtual ni instalar
dependencias a mano. El sistema completo (API + frontend web
mobile-first, mismo origen) corre dentro de un contenedor Docker.

No incluye autenticación, HTTPS ni un proxy inverso delante del
contenedor — si vas a exponer el servicio en una red no confiable (por
ejemplo, accesible desde internet), se recomienda poner un proxy como
nginx o Caddy delante, con TLS, antes de exponerlo. Esta feature no lo
configura por vos.

## Prerequisitos

- **Windows / macOS:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  instalado y corriendo.
- **Linux:** Docker Engine + el plugin `docker compose` (v2) instalados.
- Una copia del repositorio (`git clone` o el `.zip` del release), con
  `backend/config/services.ini` presente (ya viene versionado en el
  repo, no hace falta crearlo a mano en un checkout normal).

## Levantar el sistema

Desde la raíz del repositorio:

```bash
docker compose up -d
```

Este comando:

- construye la imagen (`docker build .`, primera vez) o usa la imagen ya
  construida en corridas posteriores,
- levanta el contenedor con el puerto `8000` mapeado al host,
- monta tres carpetas del host como almacenamiento persistente:
  `./storage_bridge`, `./output`, `./inbound`,
- monta `./backend/config/services.ini` como archivo de configuración
  editable sin reconstruir la imagen.

Para ver los logs en vivo:

```bash
docker compose logs -f
```

Para bajar el sistema (los datos en `storage_bridge/`, `output/` e
`inbound/` **no** se pierden, quedan en el host):

```bash
docker compose down
```

### Alternativa sin `docker-compose.yml` (`docker run`)

```bash
docker build -t gi-ocr:latest .

docker run -d \
  -p 8000:8000 \
  -v "$(pwd)/storage_bridge:/app/storage_bridge" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/inbound:/app/inbound" \
  -v "$(pwd)/backend/config/services.ini:/app/backend/config/services.ini" \
  --name gi-ocr \
  gi-ocr:latest
```

En Windows PowerShell, reemplazar `$(pwd)` por `${PWD}` o la ruta
absoluta del repo.

## Cómo apuntar los volúmenes y `services.ini`

- **`storage_bridge/`**: acá aparecen los archivos `.DATA` listos para
  que el sistema legacy los consuma (`storage_bridge/ready/`), los
  documentos entrantes (`storage_bridge/inbound/`) y los fallidos
  (`storage_bridge/failed/`). Si tu sistema legacy corre en otra máquina,
  cambiá la ruta del host en `docker-compose.yml` (columna izquierda del
  `-` en `volumes:`) para que apunte a una carpeta compartida real, por
  ejemplo un recurso de red montado en el host.
- **`output/`**: historial de jobs procesados y documentos confirmados
  por revisión humana. Útil para debugging o auditoría; podés apuntarlo
  a un disco con más espacio si esperás mucho volumen.
- **`inbound/`**: carpeta que el sistema observa automáticamente para
  encolar documentos nuevos (además de la carga manual vía frontend/API).
  Es **distinta** de `storage_bridge/inbound/`.
- **`backend/config/services.ini`**: acá se define, en texto plano, qué
  campos extraer por cada servicio/documento y con qué reglas. Para
  ajustar la configuración de un cliente sin reconstruir la imagen,
  editá directamente el archivo en el host (la ruta que aparece a la
  izquierda del `-v`/`volumes:` en el ejemplo de arriba) y reiniciá el
  contenedor:

```bash
docker compose restart
```

**Importante — primer arranque:** el archivo `backend/config/services.ini`
del host debe existir **antes** de correr `docker compose up` por
primera vez. Si no existe, Docker crea un directorio vacío en su lugar
en vez de un archivo, y el backend no arranca. En un checkout normal del
repositorio (`git clone`) el archivo ya viene versionado, así que este
caso solo aplica si lo borraste o si apuntás el volumen a una ruta fuera
del checkout — copiá el archivo real ahí antes de levantar el
contenedor.

**Importante — actualizar la imagen no actualiza `services.ini` de un
cliente:** si actualizás la imagen (por ejemplo, `docker pull` de una
versión nueva publicada en `ghcr.io`) pero el cliente ya tiene su propio
`services.ini` editado en el host, ese archivo del host sigue
gobernando — la imagen nueva no lo sobrescribe. Si necesitás propagar un
cambio de configuración por defecto, hay que copiarlo a mano a la ruta
montada de ese cliente.

## Ejemplo de uso HTTP: verificar que el sistema está arriba

Con el contenedor corriendo (`docker compose up -d`), confirmá que
responde:

**Request:**

```
GET http://localhost:8000/api/v1/health
```

```bash
curl http://localhost:8000/api/v1/health
```

**Response (`200 OK`):**

```json
{
  "status": "ok",
  "engine_loaded": true,
  "queue_workers": 2,
  "inbound": {
    "inbound_dir": "/app/inbound",
    "watching": true,
    "files_present": 0,
    "files_seen_history": 0
  }
}
```

El campo `status` siempre es `"ok"` si el proceso respondió; `engine_loaded`
indica si el motor OCR (RapidOCR/ONNX) ya terminó de inicializarse —
puede tardar unos segundos tras el arranque del contenedor, durante ese
lapso puede aparecer `false`. El resto de los campos (`queue_workers`,
`inbound`) refleja el estado real del proceso, no un valor fijo — puede
variar según configuración y versión.

Una vez confirmado el `health check`, el frontend web está disponible en
`http://localhost:8000/` (mismo origen, mismo puerto) para cargar
comprobantes desde el navegador o el celular (misma red).

## Publicar/actualizar la imagen (uso avanzado)

Las imágenes de release se publican automáticamente en
`ghcr.io/<owner>/<repo>` cuando el mantenedor del proyecto pushea un tag
`vX.Y.Z` a `main` (esto lo hace el equipo del proyecto, no cada usuario
del contenedor). Para usar una imagen ya publicada en vez de construirla
localmente:

```bash
docker pull ghcr.io/<owner>/<repo>:v1.0.0
docker run -d -p 8000:8000 \
  -v "$(pwd)/storage_bridge:/app/storage_bridge" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/inbound:/app/inbound" \
  -v "$(pwd)/backend/config/services.ini:/app/backend/config/services.ini" \
  ghcr.io/<owner>/<repo>:v1.0.0
```

Si el paquete es privado en GHCR, hace falta `docker login ghcr.io` con
un token de GitHub con permiso de lectura de paquetes antes del `pull`
(configuración de visibilidad: ver
[docs/tecnica/empaquetado-despliegue.md](../tecnica/empaquetado-despliegue.md)).
