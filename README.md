# IoT Developer con AWS

Curso teórico-práctico para diseñar, desarrollar e implementar soluciones **IoT
end-to-end sobre AWS**: desde la conexión segura del dispositivo hasta la
visualización de los datos y las alertas.

Este repositorio contiene el material, el código de los laboratorios y los
recursos de apoyo de las sesiones del curso.

---

## Información general

| | |
|---|---|
| **Duración** | 24 sesiones de 45 minutos (18 horas) |
| **Formato** | 3 sesiones por día · 8 días de curso |
| **Modalidad** | Teórico-práctica, con laboratorio en cada sesión |
| **Prerrequisitos** | Programación básica (Python de preferencia) |
| **Infraestructura** | Cuenta AWS (Free Tier) + Python 3.8 o superior |

## Objetivo general

Capacitar a los participantes en el diseño, desarrollo e implementación de
soluciones IoT completas utilizando los servicios de AWS, aplicando las mejores
prácticas de la industria en seguridad, escalabilidad y arquitectura cloud.

## Competencias a desarrollar

Al finalizar el curso, el participante será capaz de:

1. **Conectar dispositivos IoT a AWS IoT Core** de forma segura, usando MQTT y
   certificados X.509.
2. **Recolectar y filtrar datos en tiempo real** con el IoT Rules Engine y
   procesarlos con AWS Lambda.
3. **Almacenar telemetría** en la base de datos adecuada a cada caso de uso
   (DynamoDB, S3, Timestream).
4. **Visualizar datos** en dashboards interactivos con Amazon QuickSight.
5. **Implementar seguridad IoT**: políticas de mínimo privilegio, monitoreo con
   Device Defender y un sistema de alertas.
6. **Integrar múltiples servicios AWS** en soluciones end-to-end, del
   dispositivo a la aplicación.

---

## Programa

### Día 1 — Fundamentos de IoT
1. Introducción a IoT: ¿qué es y por qué AWS?
2. Arquitecturas IoT y casos de uso reales
3. Setup de AWS + simulador de dispositivo IoT

### Día 2 — Protocolos y comunicación
4. Protocolos IoT: MQTT, HTTP, CoAP
5. MQTT Pub/Sub: cliente Python básico
6. **Lab:** comunicación bidireccional con MQTT

### Día 3 — AWS IoT Core (parte 1)
7. Things, certificados y seguridad
8. **Lab:** crear un Thing y conectar el dispositivo
9. Políticas y permisos en AWS IoT

### Día 4 — AWS IoT Core (parte 2)
10. Device Shadow: el gemelo digital
11. **Lab:** Shadow para control remoto
12. Sincronización de estados y manejo offline

### Día 5 — Procesamiento de datos
13. IoT Rules Engine: SQL para IoT
14. **Lab:** filtrado y transformación de datos
15. AWS Lambda para procesamiento serverless

### Día 6 — Almacenamiento
16. DynamoDB para datos IoT
17. **Lab:** almacenar telemetría en DynamoDB
18. S3 y Timestream para datos históricos

### Día 7 — Analytics y visualización
19. AWS IoT Analytics: pipeline completo
20. **Lab:** configurar el pipeline de analytics
21. QuickSight: dashboard de monitoreo IoT

### Día 8 — Seguridad y proyecto final
22. Seguridad IoT y Device Defender
23. Monitoreo con CloudWatch y alertas
24. **Proyecto integrador:** deploy del sistema completo

---

## Proyecto final

Sistema de monitoreo completo, construido de forma incremental a lo largo del
curso:

```
Dispositivo IoT  ──►  AWS IoT Core  ──►  Rules Engine + Lambda
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                        DynamoDB + S3      QuickSight          SNS
                        (almacenamiento)   (dashboard)        (alertas)
```

---

## Requisitos previos a la primera sesión

- **Docker Desktop instalado y probado** → sigue la
  [guía de instalación paso a paso](docs/instalar-docker.md). Es la que usan
  los laboratorios; dedícale 20 minutos **antes** de la primera clase.
- Cuenta de AWS activa (el curso se trabaja dentro del **Free Tier**).
- Python 3.8 o superior instalado.
- Git y un editor de código (se recomienda VS Code).

No hace falta tener experiencia con Docker: la guía explica cada comando y
trae una sección de problemas frecuentes con su solución.

> **Importante — costos y seguridad:** los laboratorios usan servicios que
> pueden generar cargos si quedan activos. Al final de cada día se indica qué
> recursos eliminar. **Nunca** subas al repositorio certificados, claves
> privadas ni credenciales de AWS.

## Estructura del repositorio

El contenido se irá publicando por sesión a medida que avanza el curso.

```
.
├── README.md                    Este archivo
├── docs/
│   └── instalar-docker.md       Prepara tu computadora (empieza aquí)
└── labs/
    └── 02-protocolos/           Laboratorio de HTTP y MQTT
```

### Laboratorios disponibles

| Laboratorio | Qué practicas |
|---|---|
| [02 · Protocolos IoT](labs/02-protocolos/) | HTTP y MQTT paso a paso, y un banco de pruebas en vivo con broker real |

---

## Autor

**César Cruz** — FabLab ESAN
