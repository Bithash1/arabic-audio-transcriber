#include <jni.h>
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "whisper.h"

namespace {
std::string escape_json(const char *value) {
    std::ostringstream output;
    for (const unsigned char ch : std::string(value == nullptr ? "" : value)) {
        switch (ch) {
            case '\"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (ch < 0x20) {
                    output << "\\u00";
                    const char *hex = "0123456789abcdef";
                    output << hex[(ch >> 4) & 0xf] << hex[ch & 0xf];
                } else {
                    output << ch;
                }
        }
    }
    return output.str();
}

void throw_runtime(JNIEnv *env, const std::string &message) {
    jclass exception = env->FindClass("java/lang/RuntimeException");
    env->ThrowNew(exception, message.c_str());
}
}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_io_github_bithash1_arabictranscriber_transcription_NativeWhisperBridge_transcribe(
        JNIEnv *env,
        jobject,
        jstring model_path,
        jfloatArray sample_array,
        jstring language,
        jint threads) {
    const char *model_chars = env->GetStringUTFChars(model_path, nullptr);
    const char *language_chars = env->GetStringUTFChars(language, nullptr);
    whisper_context *context = nullptr;
    try {
        whisper_context_params context_params = whisper_context_default_params();
        context = whisper_init_from_file_with_params(model_chars, context_params);
        if (context == nullptr) throw std::runtime_error("无法加载 Whisper 模型，文件可能不完整。 ");

        const jsize sample_count = env->GetArrayLength(sample_array);
        std::vector<float> samples(static_cast<size_t>(sample_count));
        env->GetFloatArrayRegion(sample_array, 0, sample_count, samples.data());

        whisper_full_params params = whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);
        params.language = language_chars;
        params.translate = false;
        params.no_context = true;
        params.print_progress = false;
        params.print_realtime = false;
        params.print_timestamps = false;
        params.print_special = false;
        params.n_threads = std::max(1, static_cast<int>(threads));
        params.beam_search.beam_size = 5;

        if (whisper_full(context, params, samples.data(), static_cast<int>(samples.size())) != 0) {
            throw std::runtime_error("Whisper 转写失败。 ");
        }

        std::ostringstream json;
        json << '[';
        const int count = whisper_full_n_segments(context);
        for (int index = 0; index < count; ++index) {
            if (index > 0) json << ',';
            json << "{\"start_ms\":" << whisper_full_get_segment_t0(context, index) * 10
                 << ",\"end_ms\":" << whisper_full_get_segment_t1(context, index) * 10
                 << ",\"text\":\"" << escape_json(whisper_full_get_segment_text(context, index)) << "\"}";
        }
        json << ']';

        whisper_free(context);
        env->ReleaseStringUTFChars(model_path, model_chars);
        env->ReleaseStringUTFChars(language, language_chars);
        return env->NewStringUTF(json.str().c_str());
    } catch (const std::exception &error) {
        if (context != nullptr) whisper_free(context);
        env->ReleaseStringUTFChars(model_path, model_chars);
        env->ReleaseStringUTFChars(language, language_chars);
        throw_runtime(env, error.what());
        return nullptr;
    }
}

