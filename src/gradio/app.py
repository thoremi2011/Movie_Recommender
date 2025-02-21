"""
Gradio app to interact with the Movie Recommender API.
It sends queries to the backend and displays the recommendations.
"""
import os
import json
import gradio as gr
from src.api.recommendation_service import get_movie_recommendations, clear_cache, get_movie_df
from src.config.model_config import load_model_config, MODEL_CONFIG
from src.utils.logger import logger
import concurrent.futures
import html

# Executor para manejar operaciones pesadas en un solo worker.
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def cleanup():
    """Cleanup resources on application close"""
    executor.shutdown(wait=True)
    logger.info("Executor shutdown completed")

def predict_async(*args):
    """
    Wrapper to run recommend_movies asynchronously.
    Returns a tuple (html, debug dictionary).
    """
    try:
        logger.info("Starting predict_async")
        future = executor.submit(recommend_movies, *args)
        result = future.result()
        logger.info(f"Result in predict_async: {result[1]}")
        return result  # Retornamos directamente el resultado (html, debug)
    except Exception as e:
        logger.error(f"Error in predict_async: {e}")
        return f"Error: {str(e)}", {"error": str(e)}

def recommend_movies(query_sentence: str, model_name: str, date_from: str, date_to: str, 
                       min_popularity: float, min_rating: float, exclude_movies: list = None):
    """
    Function that calls the recommendation service and returns HTML-formatted results.
    """
    try:
        logger.info(f"Starting recommendation with model: {model_name}")
        logger.info(f"Parameters: query='{query_sentence}', dates={date_from}-{date_to}, pop={min_popularity}, rating={min_rating}")
        
        # Forzar limpieza de caché si se cambia el modelo.
        global last_used_model
        if 'last_used_model' not in globals() or last_used_model != model_name:
            logger.info(f"Model change detected: {last_used_model if 'last_used_model' in globals() else 'None'} -> {model_name}")
            last_used_model = model_name
        
        recommendations = get_movie_recommendations(
            sentence=query_sentence,
            model_name=model_name,
            date_from=date_from,
            date_to=date_to,
            min_popularity=min_popularity,
            max_popularity=11702,
            min_rating=min_rating,
            max_rating=10,
            top_k=5,
            exclude_movies=exclude_movies
        )
        
        if not recommendations:
            return "No recommendations found matching your criteria.", {"error": "No results"}
            
        # Construir el HTML con escapes para caracteres especiales.
        user_friendly = "<div style='display: flex; flex-wrap: wrap;'>"
        for rec in recommendations:
            title = rec.get("title", "Unknown")
            desc = rec.get("overview", "No Description")
            score = rec.get("score", 0.0)
            match_percentage = int(score * 100)
            # Escapar caracteres especiales para evitar errores en el DOM
            title_escaped = html.escape(title)
            desc_escaped = html.escape(desc)
            card = f"""
            <div style="flex: 1; min-width: 250px; margin: 10px; border: 1px solid #ddd; padding: 10px;">
              <h3>{title_escaped} - {match_percentage}% Match</h3>
              <p>{desc_escaped}</p>
            </div>
            """
            user_friendly += card
        user_friendly += "</div>"
        
        logger.info(f"Recommendation completed successfully for model {model_name}")
        return user_friendly, {"success": True, "model": model_name, "results": recommendations}
        
    except Exception as e:
        logger.error(f"Error in recommend_movies: {str(e)}", exc_info=True)
        return f"An error occurred: {str(e)}", {"error": str(e)}

def recommend_by_movie(selected_movie: str, model_name: str, date_from: str, date_to: str, 
                       min_popularity: float, min_rating: float):
    """
    Function for movie-based recommendation using the selected movie's overview.
    """
    try:
        df = get_movie_df()
        # Obtener el overview de la película seleccionada
        selected_movie_data = df[df['title'] == selected_movie].iloc[0]
        movie_overview = selected_movie_data['overview']
        
        return recommend_movies(
            query_sentence=movie_overview,
            model_name=model_name,
            date_from=date_from,
            date_to=date_to,
            min_popularity=min_popularity,
            min_rating=min_rating,
            exclude_movies=[selected_movie]  # Excluir la película seleccionada
        )
    except Exception as e:
        return f"Error: {str(e)}", {"error": str(e)}

def recommend_by_movie_async(*args):
    """
    Wrapper to run recommend_by_movie asynchronously.
    """
    try:
        logger.info("Starting recommend_by_movie_async")
        future = executor.submit(recommend_by_movie, *args)
        result = future.result()
        logger.info(f"Result in recommend_by_movie_async: {result[1]}")
        return result
    except Exception as e:
        logger.error(f"Error in recommend_by_movie_async: {e}")
        return f"Error: {str(e)}", {"error": str(e)}

def load_movie_titles():
    """
    Load the list of available movie titles.
    """
    df = get_movie_df()
    return sorted(df['title'].unique().tolist())

def reload_config():
    """
    Reload the configuration and update both model dropdowns.
    """
    logger.debug("Entering reload_config function")
    try:
        logger.info("Reloading config...")
        logger.info(f"CONFIG before reload: {MODEL_CONFIG}")
        updated_config = load_model_config()
        logger.info(f"CONFIG after reload: {updated_config}")
        clear_cache()
        new_choices = list(updated_config.keys())
        logger.debug("==== DEBUG INFO ====")
        logger.debug(f"Type of new_choices: {type(new_choices)}")
        logger.debug(f"Content of new_choices: {new_choices}")
        logger.debug("===================")

        return (
            {"choices": new_choices, "value": new_choices[0]},
            {"choices": new_choices, "value": new_choices[0]}
        )

    except Exception as e:
        logger.exception("Error in reload_config")  # Esto loguea el traceback completo
        error_msg = f"Error reloading config: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [], []

with gr.Blocks() as demo:
    gr.Markdown("# Movie Recommender\n")
    
    with gr.Tabs():
        # Tab: Search by Text
        with gr.TabItem("Search by Text"):
            query_input = gr.Textbox(label="What type of movie are you looking for?", 
                                     placeholder="Eg: 'A movie about a girl who can fly'")
            model_dropdown = gr.Dropdown(choices=list(MODEL_CONFIG.keys()), label="Model", value=list(MODEL_CONFIG.keys())[0])
            with gr.Accordion("Filters", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("Release Date Range")
                        date_from = gr.Textbox(label="From", placeholder="YYYY-MM-DD", value="1902-04-17",
                                               info="Format: YYYY-MM-DD")
                        date_to = gr.Textbox(label="To", placeholder="YYYY-MM-DD", value="2021-03-24",
                                             info="Format: YYYY-MM-DD")
                    with gr.Column():
                        gr.Markdown("Popularity & Rating Range")
                        popularity_range = gr.Slider(minimum=0, maximum=11702, value=0, step=100,
                                                     label="Minimum Popularity Score", interactive=True)
                        rating_range = gr.Slider(minimum=0, maximum=10, value=0, step=0.1,
                                                 label="Minimum Rating (0-10)", interactive=True)
            
            # Usamos gr.HTML en lugar de gr.Markdown para renderizar HTML complejo.
            output_html = gr.HTML(label="Recommended Movies")
            output_json = gr.JSON(label="Debug Info")
            recommend_btn = gr.Button("Get Recommendations", variant="primary")
            recommend_btn.click(
                fn=predict_async,
                inputs=[query_input, model_dropdown, date_from, date_to, popularity_range, rating_range],
                outputs=[output_html, output_json],
                show_progress=True
            )
        
        # Tab: Search by Movie
        with gr.TabItem("Search by Movie"):
            movie_dropdown = gr.Dropdown(choices=load_movie_titles(), label="Select a movie to find similar ones",
                                         info="Select a movie from our database")
            model_dropdown_movie = gr.Dropdown(choices=list(MODEL_CONFIG.keys()), label="Model",value=list(MODEL_CONFIG.keys())[0])
            with gr.Accordion("Filters", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("Release Date Range")
                        date_from_movie = gr.Textbox(label="From", placeholder="YYYY-MM-DD", value="1902-04-17",
                                                     info="Format: YYYY-MM-DD")
                        date_to_movie = gr.Textbox(label="To", placeholder="YYYY-MM-DD", value="2021-03-24",
                                                   info="Format: YYYY-MM-DD")
                    with gr.Column():
                        gr.Markdown("Popularity & Rating Range")
                        popularity_range_movie = gr.Slider(minimum=0, maximum=11702, value=0, step=100,
                                                           label="Minimum Popularity Score", interactive=True)
                        rating_range_movie = gr.Slider(minimum=0, maximum=10, value=0, step=0.1,
                                                       label="Minimum Rating (0-10)", interactive=True)
            
            output_html_movie = gr.HTML(label="Recommended Movies")
            output_json_movie = gr.JSON(label="Debug Info")
            recommend_btn_movie = gr.Button("Get Similar Movies", variant="primary")
            recommend_btn_movie.click(
                fn=recommend_by_movie_async,
                inputs=[movie_dropdown, model_dropdown_movie, date_from_movie, date_to_movie, popularity_range_movie, rating_range_movie],
                outputs=[output_html_movie, output_json_movie],
                show_progress=True
            )
    
    # Botón para recargar la configuración (actualiza ambos dropdowns de modelo)
    reload_btn = gr.Button("Reload Config")
    reload_btn.click(
        fn=reload_config,
        inputs=[],
        outputs=[model_dropdown, model_dropdown_movie],
        api_name="reload"
    )

if __name__ == "__main__":
    try:
        demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True, debug=True)
    finally:
        cleanup()