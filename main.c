#include <avr/cpufunc.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <util/delay.h>

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef F_CPU
#    define F_CPU 16000000UL
#endif

#define BIT(b) ((1U << (b)))

#define LDR_MEASUREMENT

#define SAMPLES         100U
#define SERIAL_BAUDRATE 9600UL

/**
 * @note Pinout:
 * Port B (PB7:0)
 * Port C (PC5:0)
 * Port D (PD7:0)
 * PC6/Reset
 */

#define PWM_PIN PD3  // D3 in arduino nano pinout

#define LDR_ANALOG_PIN PC0
#define LED_ANALOG_PIN PC1

typedef struct
{
    uint8_t duty;
#ifdef LDR_MEASUREMENT
    uint16_t led_raw;
    uint16_t led_mv;

    uint16_t ldr_raw;
    uint16_t ldr_mv;
#endif
} data_t;

data_t data = {0};

/****** PWM functions ******/

static void configure_pwm(void)
{
    DDRD |= BIT(PWM_PIN);

    TCCR2A |= BIT(WGM21) | BIT(WGM20);
    TCCR2B |= BIT(CS22);

    OCR2B = 0;
}

static void set_pwm(uint8_t duty)
{
    if (duty == 255)
    {
        TCCR2A &= ~BIT(COM2B1);
        PORTD |= BIT(PWM_PIN);
    }

    else if (duty == 0)
    {
        TCCR2A &= ~BIT(COM2B1);
        PORTD &= ~BIT(PWM_PIN);
    }

    else
    {
        OCR2B = duty;
        TCCR2A |= BIT(COM2B1);
    }
}

/****** ADC functions ******/

static void configure_adc(void)
{
    ADMUX |= BIT(REFS0);

    ADCSRA |= BIT(ADPS2) | BIT(ADPS1) | BIT(ADPS0);
    ADCSRA |= BIT(ADEN);
}

static uint16_t adc_read(uint8_t pin)
{
    ADMUX &= ~0x0F;
    ADMUX |= (pin & 0x07);

    ADCSRA |= BIT(ADSC);
    while (ADCSRA & BIT(ADSC));

    return ADC;
}

/****** Log and Serial/UART0 functions ******/

volatile bool received_frame = false;
volatile char frame_serial[5] = {0};
volatile uint8_t ind = 0;

ISR(USART_RX_vect)
{
    char c = UDR0;  // Assume ro receive this range: "0" -> "9"

    if (c == '\n' || c == '\r')
    {
        if (ind > 0)
        {
            frame_serial[ind] = '\0';
            ind = 0;
            received_frame = true;
        }
    }

    else if (ind < sizeof(frame_serial) - 1)
    {
        frame_serial[ind++] = c;
    }
}

static void configure_uart0(void)
{
    uint16_t baud_ubrr = (uint16_t) ((F_CPU / (8UL * SERIAL_BAUDRATE)) - 1);

    UCSR0A |= BIT(U2X0);
    UBRR0H = (uint8_t) (baud_ubrr >> 8);
    UBRR0L = (uint8_t) baud_ubrr;

    UCSR0B |= BIT(RXEN0) | BIT(TXEN0);  // Enable TX and RX
    UCSR0B |= BIT(RXCIE0);              // Enable RX complete Interrupt

    UCSR0C = 0;                           // non parity bit, 1 bit for start and end
    UCSR0C |= BIT(UCSZ01) | BIT(UCSZ00);  // 8 bit
}

static void usart0_transmit(unsigned char data)
{
    while (!(UCSR0A & BIT(UDRE0)));
    UDR0 = data;
}

static void usart0_print(const char *str)
{
    while (*str)
    {
        usart0_transmit(*str++);
    }
}

static void usart0_print_num(uint32_t num)
{
    char buf[11];
    utoa(num, buf, 10);
    usart0_print(buf);
}

static void log_status(const data_t *d)
{
    usart0_print_num(d->duty);
    usart0_print(",");
#ifdef LDR_MEASUREMENT
    usart0_print_num(d->led_raw);
    usart0_print(",");
    usart0_print_num(d->led_mv);
    usart0_print(",");
    usart0_print_num(d->ldr_raw);
    usart0_print(",");
    usart0_print_num(d->ldr_mv);
    usart0_print(",");
#endif
    usart0_print("\r\n");
}

/****** Main function ******/

int main(void)
{
    configure_pwm();
    configure_adc();
    configure_uart0();

    sei();  // Enable Interrupt

#ifdef LDR_MEASUREMENT
    usart0_print("duty,led_raw,led_mv,ldr_raw,ldr_mv,\r\n");
#else
    usart0_print("System ok\r\n");
#endif

    while (1)
    {
#ifdef LDR_MEASUREMENT
        set_pwm(data.duty);

        for (uint8_t i = 0; i < SAMPLES; i++)
        {
            data.led_raw = adc_read(LED_ANALOG_PIN);
            data.ldr_raw = adc_read(LDR_ANALOG_PIN);

            data.led_mv = (data.led_raw * 5000UL) >> 10;  // (raw * 5000mV) / 1024
            data.ldr_mv = (data.ldr_raw * 5000UL) >> 10;  // (raw * 5000mV) / 1024

            log_status(&data);
        }

        if (data.duty < 255)
        {
            data.duty += 15;
        }

        else
        {
            break;
        }

        _delay_ms(1);
#else
        if (received_frame)
        {
            data.duty = (uint8_t) strtol((const char *) frame_serial, NULL, 10);

            usart0_print("New Duty : ");
            usart0_print_num(data.duty);
            usart0_print("\r\n");
            received_frame = false;
        }

        set_pwm(data.duty);
#endif
    }

    return 0;
}
