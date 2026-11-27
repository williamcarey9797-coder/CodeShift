package com.example.app;

import javax.xml.bind.DatatypeConverter;
import java.nio.charset.StandardCharsets;

public class LegacyTokenEncoder {
    public String encode(String raw) {
        return DatatypeConverter.printBase64Binary(raw.getBytes(StandardCharsets.UTF_8));
    }
}
