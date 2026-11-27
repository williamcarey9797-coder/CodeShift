package com.example.app;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

public class LegacyTokenEncoder {
    public String encode(String raw) {
        return Base64.getEncoder().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }
}