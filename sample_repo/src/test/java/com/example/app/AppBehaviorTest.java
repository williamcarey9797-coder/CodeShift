package com.example.app;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class AppBehaviorTest{

    @Test
    void userReturnsExpectedAge(){
        User user = new User();
        assertEquals(25,user.getLegacyAge());
    }
}