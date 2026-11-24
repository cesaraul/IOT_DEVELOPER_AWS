// Genera el YAML a partir de lo que vas eligiendo.
//
// POR QUÉ ESTE ARCHIVO SE PARECE TANTO A LA PLANTILLA FINAL
//   Porque es la plantilla final. Aquí no hay traducción ni magia: cada
//   decisión que tomas arriba escribe unas líneas concretas, y lo que sale
//   es un archivo que AWS acepta tal cual.
//
//   Si quieres saber de dónde salen los nombres de las propiedades
//   —KeySchema, AttributeDefinitions, ProvisionedThroughput— no los
//   adivinamos: están en la página de documentación de cada recurso, y
//   cada bloque de la interfaz tiene el enlace a la suya.

// La forma de la dirección de la documentación es siempre la misma, así
// que se puede construir a partir del tipo de recurso.
export function enlaceDocs(tipo) {
  const partes = tipo.toLowerCase().split("::"); // AWS::DynamoDB::Table
  return (
    "https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/" +
    `aws-resource-${partes[1]}-${partes[2]}.html`
  );
}

// El nombre de una regla de IoT no admite guiones, solo guion bajo.
function nombreRegla(nombre) {
  return nombre.replace(/-/g, "_") + "_guardar";
}

// ---------------------------------------------------------------------
// Los trozos de SQL de la regla
// ---------------------------------------------------------------------

export function construirSql(e) {
  const campos = ["*"];

  if (e.anadeDispositivo) {
    campos.push(`topic(3) AS ${e.clavePart}`);
  }
  if (e.anadeMomento) {
    campos.push(
      `parse_time("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timestamp()) AS ${e.claveOrden}`
    );
  }

  let sql = `SELECT ${campos.join(", ")}\nFROM 'fablab/planta1/+/telemetria'`;

  if (e.conWhere && e.condicion.trim()) {
    sql += `\nWHERE ${e.condicion.trim()}`;
  }

  return sql;
}

// ---------------------------------------------------------------------
// La plantilla entera
// ---------------------------------------------------------------------

export function construirYaml(e) {
  const L = [];
  const hayDynamo = e.aDynamo;
  const hayS3 = e.aS3;

  L.push("# =====================================================================");
  L.push("#  CLASE 6 · El almacenamiento");
  L.push("#");
  L.push("#  Generado por el constructor. Es un archivo normal: puedes abrirlo,");
  L.push("#  leerlo y editarlo a mano cuando quieras.");
  L.push("#");
  L.push("#  OJO: aqui NO estan el objeto, el certificado, la politica, la");
  L.push("#  Lambda ni el tema de SNS. Esos ya existen en tu cuenta, creados a");
  L.push("#  mano en las clases anteriores. Una plantilla describe lo que ELLA");
  L.push("#  gestiona; si metieras aqui algo que ya existe, el despliegue");
  L.push("#  fallaria diciendo que ya esta creado.");
  L.push("# =====================================================================");
  L.push("");
  L.push('AWSTemplateFormatVersion: "2010-09-09"');
  L.push("");
  L.push("Description: >-");
  L.push("  Clase 6 - Almacenamiento. La tabla, el bucket, el rol y la regla.");
  L.push("");

  // --- Parameters ----------------------------------------------------
  L.push("# Lo que cambia de una persona a otra. Tu nombre quedo como valor por");
  L.push("# defecto, pero esto sigue siendo un parametro: otra persona puede usar");
  L.push("# esta misma plantilla y pasarle otro valor sin editar el archivo.");
  L.push("Parameters:");
  L.push("");
  L.push("  NombreObjeto:");
  L.push("    Type: String");
  L.push(`    Default: ${e.nombre}`);
  L.push('    AllowedPattern: "[a-z0-9-]+"');
  L.push("    Description: Nombre de tu dispositivo, en minusculas.");
  L.push("");
  L.push("Resources:");
  L.push("");

  // --- Tabla ---------------------------------------------------------
  if (hayDynamo) {
    L.push("  # -----------------------------------------------------------------");
    L.push("  # La tabla  ·  AWS::DynamoDB::Table");
    L.push("  # Solo se declaran las columnas que forman la clave. Las demas");
    L.push("  # aparecen solas, con lo que traiga cada mensaje.");
    L.push("  # -----------------------------------------------------------------");
    L.push("  Tabla:");
    L.push("    Type: AWS::DynamoDB::Table");
    L.push("    Properties:");
    L.push('      TableName: !Sub "${NombreObjeto}-telemetria"');
    L.push("      AttributeDefinitions:");
    L.push(`        - AttributeName: ${e.clavePart}`);
    L.push(`          AttributeType: ${e.tipoPart}`);
    if (e.claveOrden) {
      L.push(`        - AttributeName: ${e.claveOrden}`);
      L.push(`          AttributeType: ${e.tipoOrden}`);
    }
    L.push("      KeySchema:");
    L.push(`        - AttributeName: ${e.clavePart}`);
    L.push("          KeyType: HASH      # de quien es la fila");
    if (e.claveOrden) {
      L.push(`        - AttributeName: ${e.claveOrden}`);
      L.push("          KeyType: RANGE     # cuando");
    }
    if (e.capacidad === "aprovisionada") {
      L.push("      # Modo aprovisionado: el Free Tier permanente (25 unidades de");
      L.push("      # cada tipo) solo aplica aqui.");
      L.push("      ProvisionedThroughput:");
      L.push("        ReadCapacityUnits: 1");
      L.push("        WriteCapacityUnits: 1");
    } else {
      L.push("      # Bajo demanda: comodo, pero se paga desde la primera");
      L.push("      # escritura. El Free Tier permanente no lo cubre.");
      L.push("      BillingMode: PAY_PER_REQUEST");
    }
    L.push("");
  }

  // --- Bucket --------------------------------------------------------
  if (hayS3) {
    L.push("  # -----------------------------------------------------------------");
    L.push("  # El bucket  ·  AWS::S3::Bucket");
    L.push("  # Los nombres de bucket son unicos en TODO el mundo, no solo en tu");
    L.push("  # cuenta: por eso le pegamos el numero de cuenta detras.");
    L.push("  # -----------------------------------------------------------------");
    L.push("  Bucket:");
    L.push("    Type: AWS::S3::Bucket");
    L.push("    Properties:");
    L.push('      BucketName: !Sub "${NombreObjeto}-telemetria-${AWS::AccountId}"');
    L.push("      PublicAccessBlockConfiguration:");
    L.push("        BlockPublicAcls: true");
    L.push("        BlockPublicPolicy: true");
    L.push("        IgnorePublicAcls: true");
    L.push("        RestrictPublicBuckets: true");
    L.push("");
  }

  // --- Rol -----------------------------------------------------------
  L.push("  # -----------------------------------------------------------------");
  L.push("  # El rol  ·  AWS::IAM::Role");
  L.push("  # Una regla no puede escribir en tu tabla porque si: necesita una");
  L.push("  # identidad, igual que el dispositivo necesita su certificado.");
  L.push("  # -----------------------------------------------------------------");
  L.push("  RolRegla:");
  L.push("    Type: AWS::IAM::Role");
  L.push("    Properties:");
  L.push('      RoleName: !Sub "${NombreObjeto}-rol-guardar"');
  L.push("      AssumeRolePolicyDocument:");
  L.push('        Version: "2012-10-17"');
  L.push("        Statement:");
  L.push("          - Effect: Allow");
  L.push("            Principal:");
  L.push("              Service: iot.amazonaws.com");
  L.push("            Action: sts:AssumeRole");
  L.push("      Policies:");
  L.push("        - PolicyName: puede-guardar");
  L.push("          PolicyDocument:");
  L.push('            Version: "2012-10-17"');
  L.push("            Statement:");
  if (hayDynamo) {
    L.push("              # !GetAtt coge un dato de OTRO recurso de esta misma");
    L.push("              # plantilla: el permiso apunta a tu tabla y a ninguna otra.");
    L.push("              - Effect: Allow");
    L.push("                Action: dynamodb:PutItem");
    L.push("                Resource: !GetAtt Tabla.Arn");
  }
  if (hayS3) {
    L.push("              - Effect: Allow");
    L.push("                Action: s3:PutObject");
    L.push('                Resource: !Sub "${Bucket.Arn}/*"');
  }
  if (!hayDynamo && !hayS3) {
    L.push("              # Sin destinos elegidos no hay nada que permitir.");
    L.push("              # Esta plantilla todavia no sirve para nada.");
    L.push("              - Effect: Deny");
    L.push('                Action: "*"');
    L.push('                Resource: "*"');
  }
  L.push("");

  // --- Regla ---------------------------------------------------------
  L.push("  # -----------------------------------------------------------------");
  L.push("  # La regla  ·  AWS::IoT::TopicRule");
  L.push("  # -----------------------------------------------------------------");
  L.push("  ReglaGuardar:");
  L.push("    Type: AWS::IoT::TopicRule");
  L.push("    Properties:");
  L.push("      # Los nombres de regla no admiten guiones, solo guion bajo.");
  L.push("      RuleName: !Sub");
  L.push('        - "${n}_guardar"');
  L.push('        - n: !Join ["_", !Split ["-", !Ref NombreObjeto]]');
  L.push("      TopicRulePayload:");
  L.push('        AwsIotSqlVersion: "2016-03-23"');
  L.push("        RuleDisabled: false");
  if (!e.conWhere) {
    L.push("        # Sin WHERE: se filtra lo que se avisa, no lo que se guarda.");
  }
  L.push("        Sql: >-");
  for (const linea of construirSql(e).split("\n")) {
    L.push("          " + linea);
  }
  L.push("        Actions:");
  if (hayDynamo) {
    L.push("          # DynamoDBv2 escribe cada campo en su propia columna.");
    L.push("          - DynamoDBv2:");
    L.push("              PutItem:");
    L.push("                TableName: !Ref Tabla");
    L.push("              RoleArn: !GetAtt RolRegla.Arn");
  }
  if (hayS3) {
    L.push("          - S3:");
    L.push("              BucketName: !Ref Bucket");
    L.push("              # Carpetas por equipo y por dia.");
    L.push(
      "              Key: \"${topic(3)}/${parse_time('yyyy/MM/dd', timestamp())}/${newuuid()}.json\""
    );
    L.push("              RoleArn: !GetAtt RolRegla.Arn");
  }
  L.push("");

  // --- Outputs -------------------------------------------------------
  L.push("# Lo que te devuelve al terminar, para no ir a buscarlo a la consola.");
  L.push("Outputs:");
  L.push("");
  if (hayDynamo) {
    L.push("  Tabla:");
    L.push("    Description: Ponlo en TABLA, en el .env del laboratorio.");
    L.push("    Value: !Ref Tabla");
    L.push("");
  }
  if (hayS3) {
    L.push("  Bucket:");
    L.push("    Description: Ponlo en BUCKET, en el .env del laboratorio.");
    L.push("    Value: !Ref Bucket");
    L.push("");
  }
  L.push("  Regla:");
  L.push("    Value: !Ref ReglaGuardar");

  return L.join("\n") + "\n";
}

export { nombreRegla };
