# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app

# Copy pom.xml first so the dependency layer is only re-run when pom.xml changes.
COPY pom.xml .
# BuildKit cache mount: Maven local repo persists between builds — no re-download of JARs.
RUN --mount=type=cache,target=/root/.m2 \
    mvn dependency:go-offline -B

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn clean package -DskipTests -B

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/target/backend-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
