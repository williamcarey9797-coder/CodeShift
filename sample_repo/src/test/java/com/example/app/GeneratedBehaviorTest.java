package com.example.app;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class GeneratedBehaviorTest {

    @Test
    void testGetLegacyAge() {
        User user = new User();
        assertEquals(25, user.getLegacyAge());
    }
}