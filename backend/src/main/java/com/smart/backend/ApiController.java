package com.smart.backend;

import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.beans.factory.annotation.Value;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ApiController {

    private final RestTemplate restTemplate = new RestTemplate();
    
    @Value("${ai.service.url:http://127.0.0.1:8000}")
    private String fastApiBaseUrl;

    @PostMapping("/upload")
    public ResponseEntity<?> uploadFile(@RequestParam("file") MultipartFile file) {
        try {
            // Forward the file to FastAPI
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new ByteArrayResource(file.getBytes()) {
                @Override
                public String getFilename() {
                    return file.getOriginalFilename() != null ? file.getOriginalFilename() : "upload.pdf";
                }
            });

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            ResponseEntity<Map> response = restTemplate.postForEntity(
                    fastApiBaseUrl + "/process-document", requestEntity, Map.class);

            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());

        } catch (HttpStatusCodeException e) {
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", "Error from AI Service: " + e.getResponseBodyAsString()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Error calling AI Service: " + e.getMessage()));
        }
    }

    @PostMapping("/chat")
    public ResponseEntity<?> chat(@RequestBody Map<String, String> request) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, String>> requestEntity = new HttpEntity<>(request, headers);

            ResponseEntity<Map> response = restTemplate.postForEntity(
                    fastApiBaseUrl + "/chat", requestEntity, Map.class);

            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());

        } catch (HttpStatusCodeException e) {
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", "Error from AI Service: " + e.getResponseBodyAsString()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Error calling AI Service: " + e.getMessage()));
        }
    }
}
